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