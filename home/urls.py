from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("sobre/", views.sobre, name="sobre"),
    path("eventos/", views.evento_list, name="eventos"),
    path("cadastrar-evento/", views.cadastrar_evento, name="cadastrar_evento"),
    path(
        "entrar/",
        LoginView.as_view(
            template_name="home/index.html",
            extra_context={"eventos": views.Evento.objects.all()},
        ),
        name="login",
    ),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("criar-conta/", views.cadastro, name="cadastro"),
]