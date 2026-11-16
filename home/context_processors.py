from .forms import EventoForm, UsuarioCreationForm


def evento_form(request):
    context = {"evento_form": EventoForm()}
    if not request.user.is_authenticated:
        context["cadastro_form"] = UsuarioCreationForm()
    return context