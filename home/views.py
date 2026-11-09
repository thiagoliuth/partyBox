from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import EventoForm
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


def cadastrar_evento(request):
    if request.method != "POST":
        return redirect(f"{reverse('index')}#cadastro-evento")

    form = EventoForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        return redirect("index")

    return render(request, "home/index.html", {"eventos": Evento.objects.all(), "evento_form": form})
