import uuid
from django.db import models


class Class(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    studylist_url = models.URLField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    class_room = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=500)
    video_id = models.CharField(max_length=50)
    order = models.PositiveIntegerField()
    cached_video_url = models.TextField(blank=True, null=True, help_text="Cached direct video URL")
    cached_subtitles_vtt = models.TextField(blank=True, null=True, help_text="Cached VTT subtitle content")
    cached_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title}"

    def get_youtube_url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}"

    def get_embed_url(self):
        return f"https://www.youtube.com/embed/{self.video_id}"


class Membership(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    class_room = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'class_room')

    def __str__(self):
        return f"{self.user.username} in {self.class_room.name}"


class LessonProgress(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_position = models.FloatField(default=0.0, help_text="Last watch position in seconds")

    class Meta:
        unique_together = ('lesson', 'user')
        verbose_name_plural = "Lesson progress"

    def __str__(self):
        status = "✓" if self.completed else "⋯"
        return f"{status} {self.user.username} - {self.lesson.title}"


class Quiz(models.Model):
    """Quiz assessment for a lesson based on video subtitles"""
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    source_subtitles = models.TextField(help_text="JSON of extracted subtitles")
    ai_model_used = models.CharField(max_length=100, default='gemini-1.5-flash')
    generated_by_ai = models.BooleanField(default=True)
    passing_score = models.PositiveIntegerField(default=70, help_text="Percentage needed to pass")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return f"Quiz: {self.lesson.title}"

    def get_questions_count(self):
        return self.questions.count()

    def get_passing_questions_required(self):
        """Calculate how many questions need to be correct to pass"""
        total = self.get_questions_count()
        return max(1, int((self.passing_score / 100) * total))


class QuizQuestion(models.Model):
    """Individual question in a quiz"""
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    explanation = models.TextField(blank=True, null=True, help_text="Educational explanation of the answer")
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ('quiz', 'order')

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."


class QuizAnswer(models.Model):
    """Possible answers for multiple choice/true false questions"""
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.answer_text[:50]}..."


class QuizAttempt(models.Model):
    """Record of a user attempting a quiz"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0, help_text="Score as percentage")
    passed = models.BooleanField(default=False)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-completed_at']
        unique_together = ('quiz', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.quiz.lesson.title} ({self.score}%)"

    def calculate_score(self):
        """Calculate score from user responses"""
        responses = self.user_responses.filter(is_answered=True)
        correct = responses.filter(is_correct=True).count()
        total = self.quiz.get_questions_count()
        
        self.correct_answers = correct
        self.total_questions = total
        self.score = int((correct / total) * 100) if total > 0 else 0
        self.passed = self.score >= self.quiz.passing_score
        return self.score


class QuizUserResponse(models.Model):
    """User's response to a specific quiz question"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='user_responses')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(QuizAnswer, on_delete=models.SET_NULL, blank=True, null=True)
    free_text_answer = models.TextField(blank=True, null=True, help_text="For short answer questions")
    is_correct = models.BooleanField(default=False)
    is_answered = models.BooleanField(default=False)
    
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"{self.attempt.user.username} - Q{self.question.order}"