from django.contrib import messages

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import EventoForm, UsuarioCreationForm
from .models import Categoria, Evento


def index(request):
    eventos = Evento.objects.all()
    return render(request, "home/index.html", {"eventos": eventos})


def sobre(request):
    return render(request, "home/sobre.html")


def evento_list(request):
    q = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "")
    ordem = request.GET.get("ordem", "alfabetica")

    eventos = Evento.objects.select_related("categoria", "usuario")
    if q:
        eventos = eventos.filter(nome__icontains=q)
    if categoria_id.isdecimal():
        eventos = eventos.filter(categoria_id=categoria_id)

    if ordem == "data":
        eventos = eventos.order_by("dataEvento", "horarioEvento")
    else:
        ordem = "alfabetica"
        eventos = eventos.order_by("nome")

    return render(
        request,
        "home/eventos.html",
        {
            "eventos": eventos,
            "categorias": Categoria.objects.all(),
            "q": q,
            "categoria_selecionada": categoria_id,
            "ordem": ordem,
        },
    )


@login_required
def meus_eventos(request):
    ordem = request.GET.get("ordem", "nome")
    ordenacoes = {
        "nome": ("nome", "pk"),
        "data": ("dataEvento", "horarioEvento", "pk"),
    }
    if ordem not in ordenacoes:
        ordem = "nome"
    eventos = (
        Evento.objects.filter(usuario=request.user)
        .select_related("categoria")
        .order_by(*ordenacoes[ordem])
    )
    return render(request, "home/meus_eventos.html", {"eventos": eventos, "ordem": ordem})


@login_required
def editar_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk, usuario=request.user)
    if request.method == "POST":
        form = EventoForm(request.POST, request.FILES, instance=evento, prefix="editar")
        if form.is_valid():
            form.save()
            messages.success(request, "Evento atualizado com sucesso.")
            return redirect("meus_eventos")
    else:
        form = EventoForm(instance=evento, prefix="editar")
    return render(request, "home/editar_evento.html", {"form": form, "evento": evento})


@login_required
@require_POST
def excluir_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk, usuario=request.user)
    evento.delete()
    messages.success(request, "Evento excluído com sucesso.")
    return redirect("meus_eventos")


@login_required
def cadastrar_evento(request):
    if request.method != "POST":
        return redirect(f"{reverse('index')}#cadastro-evento")

    form = EventoForm(request.POST, request.FILES)
    if form.is_valid():
        evento = form.save(commit=False)
        evento.usuario = request.user
        evento.save()
        return redirect("index")

    return render(request, "home/index.html", {"eventos": Evento.objects.all(), "evento_form": form})


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method != "POST":
        return redirect(f"{reverse('index')}#modal-cadastro")

    form = UsuarioCreationForm(request.POST)
    if form.is_valid():
        usuario = form.save()
        login(request, usuario)
        return redirect("index")

    return render(
        request,
        "home/index.html",
        {"eventos": Evento.objects.all(), "cadastro_form": form},
    )