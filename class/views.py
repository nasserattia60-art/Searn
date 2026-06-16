import json
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Class, Membership, Lesson, LessonProgress
from .forms import ClassCreateForm
from .service import get_playlist_videos, get_video_direct_url, get_video_subtitles


def _ensure_lesson_cache(lesson):
    """Cache direct video URL and subtitles for a lesson if not yet cached."""
    if not lesson.cached_video_url:
        video_url = get_video_direct_url(lesson.video_id)
        if video_url:
            lesson.cached_video_url = video_url

    if not lesson.cached_subtitles_vtt:
        _, vtt_content = get_video_subtitles(lesson.video_id)
        lesson.cached_subtitles_vtt = vtt_content

    if lesson.cached_video_url or lesson.cached_subtitles_vtt:
        lesson.cached_at = timezone.now()
        lesson.save(update_fields=['cached_video_url', 'cached_subtitles_vtt', 'cached_at'])


def format_seconds_to_hms(seconds):
    """Convert float seconds to H:MM:SS string for templates."""
    if seconds is None:
        return "00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


@login_required
def home(request):
    user_classes = Membership.objects.filter(user=request.user).select_related('class_room')
    user_class_ids = user_classes.values_list('class_room_id', flat=True)
    other_classes = Class.objects.exclude(id__in=user_class_ids)
    return render(request, 'class/home.html', {
        'user_classes': user_classes,
        'other_classes': other_classes,
    })


@login_required
def create_class(request):
    if request.method == 'POST':
        form = ClassCreateForm(request.POST)
        if form.is_valid():
            class_name = form.cleaned_data['class_name']
            description = form.cleaned_data['description']
            playlist_url = form.cleaned_data['playlist_url']

            class_room = Class.objects.create(
                name=class_name,
                description=description,
                studylist_url=playlist_url,
            )

            Membership.objects.create(user=request.user, class_room=class_room)

            try:
                data = get_playlist_videos(playlist_url)
                for video in data.get("videos", []):
                    Lesson.objects.create(
                        class_room=class_room,
                        title=video["title"],
                        video_id=video["video_id"],
                        order=video["order"],
                    )
            except Exception as e:
                messages.warning(request, f"Class created but could not load playlist: {e}")

            messages.success(request, f"Class '{class_name}' created successfully!")
            return redirect('class-detail', class_id=class_room.id)
    else:
        form = ClassCreateForm()

    return render(request, 'class/create_class.html', {'form': form})


@login_required
def class_detail(request, class_id):
    class_room = get_object_or_404(Class, id=class_id)
    is_member = Membership.objects.filter(user=request.user, class_room=class_room).exists()
    lessons = Lesson.objects.filter(class_room=class_room)

    # Get progress for current user
    progress_map = {}
    if is_member:
        progresses = LessonProgress.objects.filter(
            user=request.user,
            lesson__class_room=class_room
        )
        progress_map = {p.lesson_id: p for p in progresses}

    return render(request, 'class/class_detail.html', {
        'class_room': class_room,
        'is_member': is_member,
        'lessons': lessons,
        'progress_map': progress_map,
    })


@login_required
def lesson_detail(request, lesson_uuid):
    lesson = get_object_or_404(Lesson, uuid=lesson_uuid)
    class_room = lesson.class_room
    is_member = Membership.objects.filter(user=request.user, class_room=class_room).exists()

    if not is_member:
        messages.error(request, "You must be a member to view lessons.")
        return redirect('class-detail', class_id=class_room.id)

    # Cache video URL and subtitles if needed
    _ensure_lesson_cache(lesson)

    prev_lesson = Lesson.objects.filter(class_room=class_room, order__lt=lesson.order).last()
    next_lesson = Lesson.objects.filter(class_room=class_room, order__gt=lesson.order).first()

    # Get progress
    progress, _ = LessonProgress.objects.get_or_create(
        lesson=lesson,
        user=request.user,
        defaults={'last_position': 0.0}
    )

    # Parse subtitles list for interactive display
    subtitles = []
    vtt_content = lesson.cached_subtitles_vtt or ""
    if vtt_content:
        lines = vtt_content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if "-->" in line:
                parts = line.split(" --> ")
                if len(parts) == 2:
                    start = _parse_ts(parts[0].strip())
                    end = _parse_ts(parts[1].split()[0].strip())
                    i += 1
                    # Collect text until next blank line
                    text_parts = []
                    while i < len(lines) and lines[i].strip():
                        text_parts.append(lines[i].strip())
                        i += 1
                    text = " ".join(text_parts)
                    if text:
                        subtitles.append({
                            'start': start,
                            'end': end,
                            'text': text,
                        })
            i += 1

    return render(request, 'class/lesson_detail.html', {
        'lesson': lesson,
        'class_room': class_room,
        'is_member': is_member,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'subtitles': subtitles,
        'subtitles_json': json.dumps(subtitles) if subtitles else '[]',
        'video_url': lesson.cached_video_url,
        'progress': progress,
    })


def _parse_ts(ts):
    """Parse HH:MM:SS.mmm or MM:SS.mmm to seconds float."""
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return 0.0


@login_required
def mark_completed(request, lesson_uuid):
    """Mark a lesson as completed."""
    lesson = get_object_or_404(Lesson, uuid=lesson_uuid)
    progress, _ = LessonProgress.objects.get_or_create(
        lesson=lesson,
        user=request.user,
    )
    progress.completed = not progress.completed
    progress.completed_at = timezone.now() if progress.completed else None
    progress.save()
    status = "completed" if progress.completed else "uncompleted"
    messages.success(request, f"Lesson marked as {status}.")
    return redirect('lesson-detail', lesson_uuid=lesson_uuid)


@login_required
def save_position(request, lesson_uuid):
    """Save current video position."""
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, uuid=lesson_uuid)
        position = request.POST.get('position', 0)
        progress, _ = LessonProgress.objects.get_or_create(
            lesson=lesson,
            user=request.user,
        )
        progress.last_position = float(position)
        progress.save()
    return HttpResponse("OK")


@login_required
def lesson_subtitles(request, lesson_uuid):
    """Serve subtitle VTT file for HTML5 <track> element."""
    lesson = get_object_or_404(Lesson, uuid=lesson_uuid)
    class_room = lesson.class_room
    is_member = Membership.objects.filter(user=request.user, class_room=class_room).exists()

    if not is_member:
        return HttpResponse("Forbidden", status=403)

    # Cache if needed
    _ensure_lesson_cache(lesson)

    vtt_content = lesson.cached_subtitles_vtt
    if not vtt_content:
        vtt_content = "WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nNo subtitles available\n"

    return HttpResponse(vtt_content, content_type="text/vtt")


@login_required
def join_class(request, class_id):
    class_room = get_object_or_404(Class, id=class_id)
    if Membership.objects.filter(user=request.user, class_room=class_room).exists():
        messages.info(request, "You are already a member of this class.")
    else:
        Membership.objects.create(user=request.user, class_room=class_room)
        messages.success(request, f"You joined '{class_room.name}'!")
    return redirect('class-detail', class_id=class_room.id)


@login_required
def leave_class(request, class_id):
    class_room = get_object_or_404(Class, id=class_id)
    membership = Membership.objects.filter(user=request.user, class_room=class_room)
    if membership.exists():
        membership.delete()
        messages.success(request, f"You left '{class_room.name}'.")
    else:
        messages.info(request, "You are not a member of this class.")
    return redirect('class-home')