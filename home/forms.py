from django import forms

from .models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = [
            'nome',
            'descricao',
            'dataEvento',
            'horarioEvento',
            'siglaEstado',
            'cidade',
            'bairro',
            'rua',
            'numero',
            'categoria',
            'ehPago',
            'ehPublico',
            'linkSite',
            'linkInstagram',
            'thumbnail',
            'usuario',
            'cupom_codigo',
            'cupom_descricao',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: Festival de música'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Conte um pouco sobre o evento'}),
            'dataEvento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horarioEvento': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'siglaEstado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2, 'placeholder': 'SP'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cidade'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'rua': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'ehPago': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'ehPublico': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'linkSite': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'linkInstagram': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'cupom_codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: PARTYBOX10'}),
            'cupom_descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: 10% de desconto na entrada até as 20h'}),
            'cupom_dataExpiracao': forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
            'thumbnail': forms.ClearableFileInput(attrs={'class': 'form-control form-file'}),
            'usuario': forms.Select(attrs={'class': 'form-control'}),
        }

        def clean(self):
            dados = super().clean()
            if dados.get("cupom_codigo") and not dados.get("cupom_descricao"):
                self.add_error("cupom_descricao", "Explique o que o cupom oferece")
            return dados
    
