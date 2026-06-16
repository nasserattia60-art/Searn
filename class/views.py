import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Class, Membership, Lesson
from .forms import ClassCreateForm
from .service import get_playlist_videos, get_video_direct_url, get_video_subtitles

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

    return render(request, 'class/class_detail.html', {
        'class_room': class_room,
        'is_member': is_member,
        'lessons': lessons,
    })

@login_required
def lesson_detail(request, lesson_uuid):
    lesson = get_object_or_404(Lesson, uuid=lesson_uuid)
    class_room = lesson.class_room
    is_member = Membership.objects.filter(user=request.user, class_room=class_room).exists()

    if not is_member:
        messages.error(request, "You must be a member to view lessons.")
        return redirect('class-detail', class_id=class_room.id)

    prev_lesson = Lesson.objects.filter(class_room=class_room, order__lt=lesson.order).last()
    next_lesson = Lesson.objects.filter(class_room=class_room, order__gt=lesson.order).first()

    subtitles, vtt_content = get_video_subtitles(lesson.video_id)
    video_url = get_video_direct_url(lesson.video_id)

    return render(request, 'class/lesson_detail.html', {
        'lesson': lesson,
        'class_room': class_room,
        'is_member': is_member,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'subtitles': subtitles,
        'subtitles_json': json.dumps(subtitles) if subtitles else '[]',
        'video_url': video_url,
        'vtt_content': vtt_content,
    })

@login_required
def lesson_subtitles(request, lesson_uuid):
    lesson = get_object_or_404(Lesson, uuid=lesson_uuid)
    class_room = lesson.class_room
    is_member = Membership.objects.filter(user=request.user, class_room=class_room).exists()

    if not is_member:
        return HttpResponse("Forbidden", status=403)

    subtitles, vtt_content = get_video_subtitles(lesson.video_id)

    if not vtt_content:
        return HttpResponse(
            "WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nNo subtitles available\n",
            content_type="text/vtt"
        )

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