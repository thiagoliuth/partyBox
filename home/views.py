from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Case, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EventoForm, UsuarioCreationForm
from .models import Categoria, Evento


def _eventos_por_localidade(request):
    eventos = Evento.objects.select_related("categoria", "usuario")
    pares = eventos.exclude(cidade="").exclude(siglaEstado="").values_list(
        "cidade", "siglaEstado"
    ).order_by("cidade", "siglaEstado").distinct()
    todas = "Todas as localidades"
    localidades = [{"valor": "", "rotulo": todas}]
    selecionada = ""
    nome = todas
    pedida = request.GET.get("localidade", "")
    for cidade, estado in pares:
        # Preserve the city/state boundary even for text containing '%' or '|'.
        valor = "|".join(parte.replace("%", "%25").replace("|", "%7C") for parte in (cidade, estado))
        rotulo = f"{cidade} – {estado}"
        localidades.append({"valor": valor, "rotulo": rotulo})
        if pedida == valor:
            selecionada = valor
            nome = rotulo
            eventos = eventos.filter(cidade=cidade, siglaEstado=estado)

    return eventos, {
        "localidades": localidades,
        "localidade_selecionada": selecionada,
        "localidade_nome": nome,
    }


def _mural_context(request):
    eventos, localidade = _eventos_por_localidade(request)
    hoje = timezone.localdate()
    sabado = hoje + timedelta(days=5 - hoje.weekday())
    domingo = sabado + timedelta(days=1)
    futuros = list(eventos.filter(dataEvento__gte=hoje).order_by("dataEvento", "horarioEvento", "pk"))
    destaque = futuros[0] if futuros else None
    if destaque:
        limite_foto = destaque.dataEvento + timedelta(days=7)
        destaque = next(
            (evento for evento in futuros if evento.thumbnail and evento.dataEvento <= limite_foto),
            destaque,
        )

    return {
        **localidade,
        "eventos": eventos,
        "hoje": hoje,
        "categorias": Categoria.objects.filter(pk__in=eventos.order_by().values("categoria_id")),
        "destaque": destaque,
        # Keep all real weekend events even when one is also featured.
        "eventos_fim_de_semana": [
            evento for evento in futuros if sabado <= evento.dataEvento <= domingo
        ],
        "proximos_eventos": [
            evento for evento in futuros
            if not sabado <= evento.dataEvento <= domingo and evento != destaque
        ],
    }


class MuralLoginView(LoginView):
    def get_context_data(self, **kwargs):
        return {**_mural_context(self.request), **super().get_context_data(**kwargs)}


def index(request):
    return render(request, "home/index.html", _mural_context(request))


def sobre(request):
    return render(request, "home/sobre.html")


def evento_list(request):
    q = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "")
    ordem = request.GET.get("ordem", "data")
    hoje = timezone.localdate()

    eventos, localidade = _eventos_por_localidade(request)
    if q:
        eventos = eventos.filter(nome__icontains=q)
    if categoria_id.isdecimal():
        eventos = eventos.filter(categoria_id=categoria_id)

    if ordem == "data":
        eventos = eventos.order_by(
            Case(When(dataEvento__gte=hoje, then=0), default=1),
            Case(When(dataEvento__gte=hoje, then="dataEvento")),
            Case(When(dataEvento__gte=hoje, then="horarioEvento")),
            "-dataEvento", "-horarioEvento", "pk",
        )
    else:
        ordem = "alfabetica"
        eventos = eventos.order_by("nome", "pk")

    return render(
        request,
        "home/eventos.html",
        {
            **localidade,
            "eventos": eventos,
            "categorias": Categoria.objects.all(),
            "hoje": hoje,
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
    hoje = timezone.localdate()
    futuros, encerrados = [], []
    for evento in eventos:
        (futuros if evento.dataEvento >= hoje else encerrados).append(evento)
    return render(
        request,
        "home/meus_eventos.html",
        {
            "eventos": eventos,
            "ordem": ordem,
            "hoje": hoje,
            "eventos_futuros": futuros,
            "eventos_encerrados": encerrados,
        },
    )


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

    return render(request, "home/index.html", {**_mural_context(request), "evento_form": form})


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
        {**_mural_context(request), "cadastro_form": form},
    )
