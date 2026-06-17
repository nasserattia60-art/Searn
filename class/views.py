import json
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import (
    Class, Membership, Lesson, LessonProgress, 
    Quiz, QuizQuestion, QuizAnswer, QuizAttempt, QuizUserResponse
)
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
def dashboard(request):
    user = request.user
    memberships = Membership.objects.filter(user=user).select_related('class_room')
    class_ids = memberships.values_list('class_room_id', flat=True)
    classes = Class.objects.filter(id__in=class_ids)

    total_lessons = Lesson.objects.filter(class_room__in=classes).count()
    completed_progress = LessonProgress.objects.filter(user=user, completed=True)
    completed_lessons = completed_progress.count()

    # Stats
    stats = {
        'total_classes': classes.count(),
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'completion_rate': (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0,
    }

    # Per-class progress
    classes_with_progress = []
    for cls in classes:
        lesson_ids = cls.lessons.values_list('id', flat=True)
        completed_count = completed_progress.filter(lesson_id__in=lesson_ids).count()
        total = len(lesson_ids)
        classes_with_progress.append({
            'class_room': cls,
            'completed': completed_count,
            'total': total,
            'percent': (completed_count / total * 100) if total > 0 else 0,
        })

    # In-progress lessons (not completed, has last_position > 0)
    in_progress = LessonProgress.objects.filter(
        user=user,
        last_position__gt=0,
    ).exclude(completed=True).select_related('lesson__class_room').order_by('-lesson__created_at')[:5]

    # Recent activity
    recent_activity = LessonProgress.objects.filter(
        user=user,
    ).select_related('lesson').order_by('-completed_at', '-lesson__created_at')[:10]

    return render(request, 'class/dashboard.html', {
        'stats': stats,
        'classes_with_progress': classes_with_progress,
        'in_progress': in_progress,
        'recent_activity': recent_activity,
    })


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


# Quiz Views - AI-Powered Assessment
@login_required
def quiz_list(request, class_id):
    """Display all quizzes for a class"""
    class_room = get_object_or_404(Class, id=class_id)
    
    # Check membership
    if not Membership.objects.filter(user=request.user, class_room=class_room).exists():
        messages.error(request, "You are not a member of this class.")
        return redirect('class-home')
    
    lessons = class_room.lessons.all()
    quizzes = []
    
    for lesson in lessons:
        if hasattr(lesson, 'quiz'):
            quiz = lesson.quiz
            # Get user's best attempt
            attempt = quiz.attempts.filter(user=request.user).order_by('-score').first()
            quizzes.append({
                'quiz': quiz,
                'lesson': lesson,
                'attempt': attempt,
                'status': 'completed' if attempt and attempt.passed else 'pending'
            })
    
    return render(request, 'class/quiz_list.html', {
        'class_room': class_room,
        'quizzes': quizzes,
    })


@login_required
def quiz_detail(request, lesson_id):
    """Display quiz questions for a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    quiz = getattr(lesson, 'quiz', None)
    
    if not quiz:
        messages.error(request, "This lesson does not have a quiz yet.")
        return redirect('lesson-detail', lesson_id=lesson_id)
    
    # Check class membership
    if not Membership.objects.filter(
        user=request.user, 
        class_room=lesson.class_room
    ).exists():
        messages.error(request, "You are not a member of this class.")
        return redirect('class-home')
    
    # Get or create attempt
    attempt, created = quiz.attempts.get_or_create(user=request.user)
    
    # Get questions with answers
    questions = quiz.questions.all().prefetch_related('answers')
    
    # Get existing responses if this is a retry
    user_responses = {
        resp.question_id: resp 
        for resp in attempt.user_responses.all()
    }
    
    questions_with_responses = []
    for q in questions:
        response = user_responses.get(q.id)
        questions_with_responses.append({
            'question': q,
            'response': response,
            'selected_answer_id': response.selected_answer_id if response else None,
            'free_text_answer': response.free_text_answer if response else ''
        })
    
    return render(request, 'class/quiz_detail.html', {
        'quiz': quiz,
        'lesson': lesson,
        'attempt': attempt,
        'questions_with_responses': questions_with_responses,
        'completed': attempt.completed_at is not None,
    })


@login_required
def quiz_submit_response(request, lesson_id, question_id):
    """Handle quiz question submission"""
    from django.http import JsonResponse
    from .models import Quiz, QuizQuestion, QuizAnswer, QuizAttempt, QuizUserResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        lesson = get_object_or_404(Lesson, id=lesson_id)
        quiz = getattr(lesson, 'quiz', None)
        
        if not quiz:
            return JsonResponse({'error': 'Quiz not found'}, status=404)
        
        # Check membership
        if not Membership.objects.filter(
            user=request.user, 
            class_room=lesson.class_room
        ).exists():
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get question and attempt
        question = get_object_or_404(QuizQuestion, id=question_id, quiz=quiz)
        attempt = get_object_or_404(QuizAttempt, quiz=quiz, user=request.user)
        
        # Create or update response
        response_obj, created = QuizUserResponse.objects.get_or_create(
            attempt=attempt,
            question=question
        )
        
        # Process response based on question type
        if question.question_type == 'multiple_choice':
            answer_id = request.POST.get('answer_id')
            if answer_id:
                answer = get_object_or_404(QuizAnswer, id=answer_id, question=question)
                response_obj.selected_answer = answer
                response_obj.is_correct = answer.is_correct
                response_obj.is_answered = True
        
        elif question.question_type == 'true_false':
            answer_id = request.POST.get('answer_id')
            if answer_id:
                answer = get_object_or_404(QuizAnswer, id=answer_id, question=question)
                response_obj.selected_answer = answer
                response_obj.is_correct = answer.is_correct
                response_obj.is_answered = True
        
        elif question.question_type == 'short_answer':
            text_answer = request.POST.get('text_answer', '').strip()
            if text_answer:
                response_obj.free_text_answer = text_answer
                response_obj.is_answered = True
                # For short answers, mark as correct (will be reviewed by instructor)
                response_obj.is_correct = True
        
        response_obj.save()
        
        return JsonResponse({
            'success': True,
            'is_correct': response_obj.is_correct,
            'explanation': question.explanation
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def quiz_results(request, lesson_id):
    """Display quiz results and score"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    quiz = getattr(lesson, 'quiz', None)
    
    if not quiz:
        messages.error(request, "This lesson does not have a quiz.")
        return redirect('lesson-detail', lesson_id=lesson_id)
    
    attempt = get_object_or_404(QuizAttempt, quiz=quiz, user=request.user)
    
    if not attempt.completed_at:
        messages.info(request, "Quiz not yet completed.")
        return redirect('quiz-detail', lesson_id=lesson_id)
    
    # Get all responses with questions
    responses = attempt.user_responses.all().select_related(
        'question', 'selected_answer'
    )
    
    return render(request, 'class/quiz_results.html', {
        'quiz': quiz,
        'lesson': lesson,
        'attempt': attempt,
        'responses': responses,
        'passed': attempt.passed,
        'score': attempt.score,
        'passing_score': quiz.passing_score,
    })


@login_required
def quiz_retry(request, lesson_id):
    """Allow user to retry a quiz"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    quiz = getattr(lesson, 'quiz', None)
    
    if not quiz:
        messages.error(request, "This lesson does not have a quiz.")
        return redirect('lesson-detail', lesson_id=lesson_id)
    
    # Delete previous attempt to start fresh
    quiz.attempts.filter(user=request.user).delete()
    
    messages.success(request, "Quiz reset. You can now retake it.")
    return redirect('quiz-detail', lesson_id=lesson_id)
    return redirect('class-home')