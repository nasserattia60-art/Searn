"""
Django signals for automatic quiz handling and lesson completion
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import (
    Quiz, QuizAttempt, QuizUserResponse, LessonProgress, 
    Lesson, QuizAnswer
)


@receiver(post_save, sender=Lesson)
def create_quiz_on_lesson_created(sender, instance, created, **kwargs):
    """
    Signal to automatically generate quiz when a lesson is created.
    This applies learning science principles to the generated content.
    """
    if created and not hasattr(instance, 'quiz'):
        from .service import create_quiz_from_lesson
        
        # Create quiz asynchronously (in production, use Celery)
        try:
            create_quiz_from_lesson(
                lesson=instance,
                use_ai=True,
                num_questions=5
            )
        except Exception as e:
            # Log error but don't fail lesson creation
            print(f"Failed to create quiz for lesson {instance.id}: {e}")


@receiver(post_save, sender=QuizUserResponse)
def update_quiz_attempt_on_response(sender, instance, created, **kwargs):
    """
    Signal to update quiz attempt score when a response is submitted.
    Implements active recall and immediate feedback (learning science principles).
    """
    if created or kwargs.get('update_fields'):
        attempt = instance.attempt
        
        # Calculate current score
        score = attempt.calculate_score()
        attempt.save(update_fields=[
            'correct_answers', 'total_questions', 'score', 'passed'
        ])
        
        # Check if all questions are answered
        total_questions = attempt.quiz.get_questions_count()
        answered = attempt.user_responses.filter(is_answered=True).count()
        
        # If all questions answered, mark attempt as completed
        if answered == total_questions and not attempt.completed_at:
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=['completed_at'])
            
            # Trigger lesson completion if quiz is passed
            if attempt.passed:
                mark_lesson_completed(attempt)


@receiver(post_save, sender=QuizAttempt)
def auto_complete_lesson_on_quiz_pass(sender, instance, created, **kwargs):
    """
    Signal to automatically mark lesson as completed when quiz is passed.
    This reinforces the learning cycle and implements spaced repetition trigger.
    """
    if not created and instance.passed and instance.completed_at:
        # Check if lesson is not already completed
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            lesson=instance.quiz.lesson,
            user=instance.user
        )
        
        if not lesson_progress.completed:
            lesson_progress.completed = True
            lesson_progress.completed_at = timezone.now()
            lesson_progress.save()
            
            # Log this event for analytics
            print(f"✓ Lesson completed: {instance.user.username} - "
                  f"{instance.quiz.lesson.title} (Score: {instance.score}%)")


def mark_lesson_completed(attempt):
    """Helper function to mark lesson as completed after quiz pass"""
    lesson_progress, _ = LessonProgress.objects.get_or_create(
        lesson=attempt.quiz.lesson,
        user=attempt.user
    )
    
    if not lesson_progress.completed:
        lesson_progress.completed = True
        lesson_progress.completed_at = timezone.now()
        lesson_progress.save()


@receiver(post_save, sender=QuizAnswer)
def ensure_single_correct_answer(sender, instance, **kwargs):
    """
    Signal to ensure only one correct answer per question in multiple choice.
    This prevents ambiguous quiz questions.
    """
    if instance.is_correct:
        # For multiple choice and true/false questions
        if instance.question.question_type in ['multiple_choice', 'true_false']:
            # Mark other answers as incorrect
            instance.question.answers.exclude(id=instance.id).update(is_correct=False)
