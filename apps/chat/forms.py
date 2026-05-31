from django import forms
from .models import Message, Channel


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('content',)
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Napisz wiadomość...',
                'autocomplete': 'off',
            })
        }


class ChannelForm(forms.ModelForm):
    """Form for creating a top-level server (no parent)."""
    password_raw = forms.CharField(
        label='Hasło (tylko dla prywatnych)',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Zostaw puste dla publicznych'}),
    )

    class Meta:
        model = Channel
        fields = ('name', 'description', 'channel_type')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'moj-serwer'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'channel_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_channel_type'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('channel_type') == Channel.ChannelType.PRIVATE and not cleaned.get('password_raw'):
            self.add_error('password_raw', 'Prywatny serwer wymaga hasła.')
        return cleaned


class SubChannelForm(forms.ModelForm):
    """Form for creating a sub-channel (text or voice) inside a server."""
    class Meta:
        model = Channel
        fields = ('name', 'sub_type')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ogolny'}),
            'sub_type': forms.Select(attrs={'class': 'form-select'}),
        }


class JoinPrivateChannelForm(forms.Form):
    password = forms.CharField(
        label='Hasło serwera',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Wpisz hasło...'}),
    )


class AttachmentUploadForm(forms.Form):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
