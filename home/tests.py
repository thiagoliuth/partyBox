from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import EventoForm
from .models import Evento


class CadastroEventoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="organizador", email="organizador@example.com", password="senha-teste"
        )
        cls.outro_usuario = get_user_model().objects.create_user(
            username="outro", email="outro@example.com", password="senha-teste"
        )

    def setUp(self):
        self.url = reverse("cadastrar_evento")
        self.dados = {
            "nome": "Festival",
            "descricao": "Festival de música",
            "dataEvento": "2030-12-01",
            "horarioEvento": "18:00",
            "siglaEstado": "SP",
            "cidade": "São Paulo",
            "bairro": "Centro",
            "rua": "Rua do Festival",
            "numero": "10",
            "ehPublico": "on",
        }

    def test_anonimo_get_e_post_exigem_login(self):
        for metodo in ("get", "post"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.url, self.dados if metodo == "post" else {})

                self.assertRedirects(
                    response,
                    f"{reverse('admin:login')}?next={self.url}",
                    fetch_redirect_response=False,
                )
                self.assertFalse(Evento.objects.exists())

    def test_autenticado_cria_evento_sem_enviar_usuario(self):
        self.client.force_login(self.usuario)

        response = self.client.post(self.url, self.dados)

        self.assertRedirects(response, reverse("index"))
        self.assertEqual(Evento.objects.count(), 1)
        self.assertEqual(Evento.objects.get().usuario, self.usuario)

    def test_usuario_forjado_nao_altera_dono_do_evento(self):
        self.client.force_login(self.usuario)
        self.dados["usuario"] = self.outro_usuario.pk

        response = self.client.post(self.url, self.dados)

        self.assertRedirects(response, reverse("index"))
        self.assertEqual(Evento.objects.count(), 1)
        self.assertEqual(Evento.objects.get().usuario, self.usuario)

    def test_formulario_nao_expoe_usuario(self):
        form = EventoForm()

        self.assertNotIn("usuario", form.fields)
        self.assertNotIn("usuario", form.Meta.widgets)
        self.assertNotIn('name="usuario"', form.as_p())
