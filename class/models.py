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