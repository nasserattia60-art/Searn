from django import forms


class ClassCreateForm(forms.Form):
    class_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Class Name"
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Description"
    )
    playlist_url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.youtube.com/playlist?list=...'
        }),
        label="YouTube Playlist URL",
        help_text="Paste the full YouTube playlist link. All videos will be extracted and saved as lessons."
    )