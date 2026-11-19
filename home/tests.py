from datetime import date, time
from unittest.mock import patch

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from .forms import EventoForm
from .models import Categoria, Evento


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
                    f"{reverse('login')}?next={self.url}",
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


class MeusEventosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="dono", email="dono@example.com", password="senha-teste"
        )
        cls.outro_usuario = get_user_model().objects.create_user(
            username="visitante", email="visitante@example.com", password="senha-teste"
        )
        dados = {
            "descricao": "Descrição",
            "siglaEstado": "SP",
            "cidade": "São Paulo",
            "bairro": "Centro",
            "rua": "Rua",
            "numero": "1",
        }
        cls.eventos = [
            Evento.objects.create(
                usuario=cls.usuario, nome=nome, dataEvento=data,
                horarioEvento=horario, **dados
            )
            for nome, data, horario in [
                ("Zulu", "2030-12-02", "09:00"),
                ("Alfa", "2030-12-01", "18:00"),
                ("Alfa", "2030-12-01", "09:00"),
                ("Beta", "2030-12-01", "09:00"),
            ]
        ]

    def setUp(self):
        self.url = reverse("meus_eventos")

    def test_anonimo_get_e_post_exigem_login(self):
        for metodo in ("get", "post"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.url)
                self.assertRedirects(
                    response, f"{reverse('login')}?next={self.url}",
                    fetch_redirect_response=False,
                )

    def test_lista_apenas_eventos_do_usuario_com_categoria_precarregada(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url, {"usuario": self.outro_usuario.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/meus_eventos.html")
        self.assertEqual(set(response.context["eventos"]), set(self.eventos))
        self.assertEqual(response.context["eventos"].query.select_related, {"categoria": {}})

        self.client.force_login(self.outro_usuario)
        response = self.client.get(self.url, {"usuario": self.usuario.pk})
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["eventos"], [])

    def test_ordem_nome_padrao_e_desempate_por_pk(self):
        self.client.force_login(self.usuario)
        for parametros in ({}, {"ordem": "nome"}):
            with self.subTest(parametros=parametros):
                response = self.client.get(self.url, parametros)
                self.assertEqual(response.context["ordem"], "nome")
                self.assertEqual(
                    list(response.context["eventos"]),
                    [self.eventos[i] for i in (1, 2, 3, 0)],
                )

    def test_ordem_data_horario_e_desempate_por_pk(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url, {"ordem": "data"})
        self.assertEqual(response.context["ordem"], "data")
        self.assertEqual(
            list(response.context["eventos"]),
            [self.eventos[i] for i in (2, 3, 1, 0)],
        )

    def test_ordem_invalida_retorna_nome(self):
        self.client.force_login(self.usuario)
        for ordem in ("", "-nome", "usuario", "dataEvento", "?", "alfabetica"):
            with self.subTest(ordem=ordem):
                response = self.client.get(self.url, {"ordem": ordem})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["ordem"], "nome")
                self.assertEqual(
                    list(response.context["eventos"]),
                    [self.eventos[i] for i in (1, 2, 3, 0)],
                )

    def test_estado_vazio_sem_eventos(self):
        Evento.objects.all().delete()
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context["eventos"], [])
        self.assertEqual(response.context["ordem"], "nome")
        self.assertContains(response, "Você ainda não cadastrou eventos.")
        self.assertContains(response, "data-evento-open")

    def test_navegacao_exclusiva_para_autenticados(self):
        response = self.client.get(reverse("index"))
        self.assertNotContains(response, f'href="{self.url}"')
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        self.assertContains(response, f'href="{self.url}"')

    def test_links_de_edicao(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.url)
        for evento in self.eventos:
            self.assertContains(response, f'href="{reverse("editar_evento", args=[evento.pk])}"')

    def test_opcao_de_ordenacao_selecionada(self):
        self.client.force_login(self.usuario)
        for ordem, esperado in (("nome", "nome"), ("data", "data"), ("invalida", "nome")):
            with self.subTest(ordem=ordem):
                response = self.client.get(self.url, {"ordem": ordem})
                self.assertRegex(
                    response.content.decode(),
                    rf'<option\s+value="{esperado}"\s+selected(?:="selected")?\s*>',
                )

    def test_html_nao_expoe_eventos_de_outro_usuario_nem_com_pk_injetado(self):
        outro = Evento.objects.create(
            usuario=self.outro_usuario, nome="Evento secreto de outro dono",
            dataEvento="2030-12-01", horarioEvento="12:00",
        )
        self.client.force_login(self.usuario)
        response = self.client.get(self.url, {"pk": outro.pk, "usuario": self.outro_usuario.pk})
        self.assertNotContains(response, outro.nome)
        self.assertEqual(set(response.context["eventos"]), set(self.eventos))


class EdicaoEventoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="editor", email="editor@example.com", password="senha-teste"
        )
        cls.outro_usuario = get_user_model().objects.create_user(
            username="intruso", email="intruso@example.com", password="senha-teste"
        )
        cls.evento = Evento.objects.create(
            usuario=cls.usuario, nome="Original", descricao="Descrição original",
            dataEvento="2030-12-01", horarioEvento="18:30", siglaEstado="SP",
            cidade="São Paulo", bairro="Centro", rua="Rua original", numero="10",
            cupom_codigo="ANTES", cupom_descricao="Desconto original",
        )

    def setUp(self):
        self.editar = reverse("editar_evento", args=[self.evento.pk])
        self.excluir = reverse("excluir_evento", args=[self.evento.pk])
        self.dados = {
            f"editar-{campo}": valor for campo, valor in {
                "nome": "Atualizado", "descricao": "Nova descrição",
                "dataEvento": "2031-02-03", "horarioEvento": "09:15",
                "siglaEstado": "RJ", "cidade": "Rio de Janeiro", "bairro": "Novo",
                "rua": "Nova rua", "numero": "20", "ehPublico": "on",
                "cupom_codigo": "NOVO", "cupom_descricao": "Novo desconto",
            }.items()
        }

    def assertEventoInalterado(self):
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.nome, "Original")
        self.assertEqual(self.evento.usuario, self.usuario)
        self.assertEqual(self.evento.cupom_codigo, "ANTES")

    def test_anonimos_get_e_post_nas_tres_rotas_exigem_login(self):
        for url in (reverse("meus_eventos"), self.editar, self.excluir):
            for metodo in ("get", "post"):
                with self.subTest(url=url, metodo=metodo):
                    response = getattr(self.client, metodo)(url)
                    self.assertRedirects(
                        response, f"{reverse('login')}?next={url}",
                        fetch_redirect_response=False,
                    )
        self.assertEventoInalterado()

    def test_get_dono_formulario_preenchido_com_prefixo_e_data_iso(self):
        self.client.force_login(self.usuario)
        response = self.client.get(self.editar)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/editar_evento.html")
        form = response.context["form"]
        self.assertEqual(response.context["evento"], self.evento)
        self.assertEqual(form.prefix, "editar")
        self.assertEqual(form["nome"].value(), "Original")
        self.assertIn('name="editar-nome"', str(form["nome"]))
        self.assertIn('id="id_editar-nome"', str(form["nome"]))
        self.assertIn('value="2030-12-01"', str(form["dataEvento"]))
        self.assertIn('value="18:30"', str(form["horarioEvento"]))
        self.assertNotIn("usuario", form.fields)

    def test_post_valido_atualiza_campos_preserva_dono_e_mostra_sucesso(self):
        self.client.force_login(self.usuario)
        self.dados.update({"editar-usuario": self.outro_usuario.pk, "usuario": self.outro_usuario.pk})
        response = self.client.post(self.editar, self.dados)
        self.assertRedirects(response, reverse("meus_eventos"))
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.usuario, self.usuario)
        for campo in ("nome", "descricao", "siglaEstado", "cidade", "bairro", "rua",
                      "numero", "cupom_codigo", "cupom_descricao"):
            self.assertEqual(getattr(self.evento, campo), self.dados[f"editar-{campo}"])
        self.assertEqual(self.evento.dataEvento.isoformat(), "2031-02-03")
        self.assertEqual(self.evento.horarioEvento.isoformat(), "09:15:00")
        self.assertTrue(any(m.level == messages.SUCCESS for m in get_messages(response.wsgi_request)))

    def test_post_invalido_mostra_erros_sem_mutacao(self):
        self.client.force_login(self.usuario)
        self.dados["editar-nome"] = ""
        response = self.client.post(self.editar, self.dados)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/editar_evento.html")
        self.assertIn("nome", response.context["form"].errors)
        self.assertTrue(response.context["form"].is_bound)
        self.assertEventoInalterado()

    def test_dono_exclui_por_post_com_redirecionamento_e_sucesso(self):
        self.client.force_login(self.usuario)
        response = self.client.post(self.excluir)
        self.assertRedirects(response, reverse("meus_eventos"))
        self.assertFalse(Evento.objects.filter(pk=self.evento.pk).exists())
        self.assertTrue(any(m.level == messages.SUCCESS for m in get_messages(response.wsgi_request)))

    def test_exclusao_rejeita_metodos_diferentes_de_post(self):
        self.client.force_login(self.usuario)
        for metodo in ("get", "put", "patch", "delete", "head", "options"):
            with self.subTest(metodo=metodo):
                response = getattr(self.client, metodo)(self.excluir)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["Allow"], "POST")
                self.assertEventoInalterado()

    def test_outro_usuario_recebe_404_sem_mutacao(self):
        self.client.force_login(self.outro_usuario)
        for metodo, url in (("get", self.editar), ("post", self.editar), ("post", self.excluir)):
            with self.subTest(metodo=metodo, url=url):
                response = getattr(self.client, metodo)(url, self.dados if metodo == "post" else {})
                self.assertEqual(response.status_code, 404)
                self.assertEventoInalterado()

    def test_pk_inexistente_recebe_404(self):
        self.client.force_login(self.usuario)
        for metodo, nome in (("get", "editar_evento"), ("post", "editar_evento"),
                             ("post", "excluir_evento")):
            with self.subTest(metodo=metodo, nome=nome):
                response = getattr(self.client, metodo)(
                    reverse(nome, args=[self.evento.pk + 1000]),
                    self.dados if metodo == "post" else {},
                )
                self.assertEqual(response.status_code, 404)
        self.assertEventoInalterado()

    def test_exclusao_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        response = client.post(self.excluir)
        self.assertEqual(response.status_code, 403)
        self.assertEventoInalterado()


class DescobertaEventosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="agenda", email="agenda@example.com", password="senha-teste"
        )
        cls.musica = Categoria.objects.create(tipo=Categoria.CategoriaType.MUSICA)
        cls.arte = Categoria.objects.create(tipo=Categoria.CategoriaType.ARTE)
        cls.ontem = cls.criar_evento("Beta ontem", 5)
        cls.passado = cls.criar_evento("Alfa passado", 1)
        cls.hoje = cls.criar_evento("Zulu hoje", 6, ehPublico=False)
        cls.sabado = cls.criar_evento("Festival sábado", 7, thumbnail="thumbnails/sabado.jpg")
        cls.domingo = cls.criar_evento("Festival domingo", 8)
        cls.segunda = cls.criar_evento("Festival segunda", 9, horarioEvento=time(9))
        cls.segunda_tarde = cls.criar_evento("Festival segunda à tarde", 9)
        cls.outra_uf = cls.criar_evento("Festival outra UF", 10, siglaEstado="MG", categoria=cls.arte)
        cls.cidade_especial = cls.criar_evento("Cidade especial", 11, cidade="A|B%")

    @classmethod
    def criar_evento(cls, nome, dia, **campos):
        dados = {
            "horarioEvento": time(18),
            "siglaEstado": "SP",
            "cidade": "São Paulo",
            "categoria": cls.musica,
        }
        return Evento.objects.create(
            usuario=cls.usuario, nome=nome, dataEvento=date(2030, 12, dia), **(dados | campos)
        )

    def setUp(self):
        calendario = patch("home.views.timezone.localdate", return_value=date(2030, 12, 6))
        self.calendario = calendario.start()
        self.addCleanup(calendario.stop)

    def test_mural_fim_de_semana_atual_ou_proximo_sem_eventos_passados(self):
        for dia, esperados in (
            (6, [self.sabado, self.domingo]),
            (7, [self.sabado, self.domingo]),
            (8, [self.domingo]),
            (9, []),
        ):
            with self.subTest(dia=dia):
                self.calendario.return_value = date(2030, 12, dia)
                response = self.client.get(reverse("index"), {"localidade": "São Paulo|SP"})
                self.assertEqual(response.context["eventos_fim_de_semana"], esperados)
                self.assertNotIn(self.ontem, response.context["proximos_eventos"])
                self.assertFalse(set(esperados) & set(response.context["proximos_eventos"]))

    def test_mural_prioriza_foto_proxima_sem_esvaziar_fim_de_semana(self):
        response = self.client.get(reverse("index"), {"localidade": "São Paulo|SP"})
        self.assertEqual(response.context["destaque"], self.sabado)
        self.assertIn(self.sabado, response.context["eventos_fim_de_semana"])
        self.assertEqual(
            response.context["proximos_eventos"], [self.hoje, self.segunda, self.segunda_tarde]
        )
        self.calendario.return_value = date(2030, 12, 12)
        response = self.client.get(reverse("index"))
        self.assertIsNone(response.context["destaque"])
        self.assertEqual(response.context["proximos_eventos"], [])

    def test_localidades_exatas_e_categorias_coerentes(self):
        for rota in ("index", "eventos"):
            with self.subTest(rota=rota):
                url = reverse(rota)
                contexto = self.client.get(url, {"localidade": "São Paulo|MG"}).context
                self.assertEqual(contexto["localidades"][0], {"valor": "", "rotulo": "Todas as localidades"})
                self.assertEqual(contexto["localidade_selecionada"], "São Paulo|MG")
                self.assertEqual(contexto["localidade_nome"], "São Paulo – MG")
                self.assertQuerySetEqual(contexto["eventos"], [self.outra_uf])
                categorias = [self.arte] if rota == "index" else [self.arte, self.musica]
                self.assertQuerySetEqual(contexto["categorias"], categorias)

                token = next(
                    item["valor"] for item in contexto["localidades"] if item["rotulo"] == "A|B% – SP"
                )
                self.assertNotEqual(token, "A|B%|SP")
                contexto = self.client.get(url, {"localidade": token}).context
                self.assertQuerySetEqual(contexto["eventos"], [self.cidade_especial])

                contexto = self.client.get(url, {"localidade": "são paulo|mg"}).context
                self.assertEqual(contexto["localidade_selecionada"], "")
                self.assertEqual(contexto["localidade_nome"], "Todas as localidades")
                self.assertIn(self.hoje, contexto["eventos"])
                self.assertIn(self.outra_uf, contexto["eventos"])

    def test_eventos_ordenam_datas_e_combinam_filtros_sem_alterar_alfabetica(self):
        url = reverse("eventos")
        local = {"localidade": "São Paulo|SP"}
        cronologia = [
            self.hoje, self.sabado, self.domingo, self.segunda, self.segunda_tarde,
            self.ontem, self.passado,
        ]
        for filtros in (local, {**local, "ordem": "data"}):
            contexto = self.client.get(url, filtros).context
            self.assertEqual(contexto["ordem"], "data")
            self.assertEqual(contexto["hoje"], self.hoje.dataEvento)
            self.assertQuerySetEqual(contexto["eventos"], cronologia)

        contexto = self.client.get(url, {**local, "ordem": "alfabetica"}).context
        self.assertQuerySetEqual(contexto["eventos"], sorted(cronologia, key=lambda evento: evento.nome))
        contexto = self.client.get(
            url, {**local, "q": "  feSTival ", "categoria": self.musica.pk, "ordem": "data"}
        ).context
        self.assertEqual(contexto["q"], "feSTival")
        self.assertEqual(contexto["categoria_selecionada"], str(self.musica.pk))
        self.assertQuerySetEqual(contexto["eventos"], cronologia[1:5])
        contexto = self.client.get(url, {**local, "categoria": self.arte.pk}).context
        self.assertQuerySetEqual(contexto["eventos"], [])

    def test_colecao_separa_hoje_de_encerrados_preservando_ordem_e_dono(self):
        outro = get_user_model().objects.create_user(username="outro-agenda", email="outro@example.com")
        self.outra_uf.usuario = outro
        self.outra_uf.save(update_fields=["usuario"])
        self.client.force_login(self.usuario)
        contexto = self.client.get(reverse("meus_eventos"), {"ordem": "data"}).context
        self.assertEqual(contexto["hoje"], self.hoje.dataEvento)
        self.assertEqual(contexto["eventos_encerrados"], [self.passado, self.ontem])
        self.assertEqual(
            contexto["eventos_futuros"],
            [self.hoje, self.sabado, self.domingo, self.segunda, self.segunda_tarde, self.cidade_especial],
        )

    def test_respostas_de_autenticacao_e_cadastro_conservam_contexto_e_erros(self):
        filtros = "?localidade=S%C3%A3o+Paulo%7CSP"
        login_url = reverse("login") + filtros
        next_url = reverse("meus_eventos")
        respostas = [
            (self.client.get(login_url + f"&next={next_url}"), "form", None),
            (
                self.client.post(login_url, {"username": self.usuario.username, "password": "errada", "next": next_url}),
                "form",
                "__all__",
            ),
            (
                self.client.post(reverse("cadastro") + filtros, {"username": "perfil-novo"}),
                "cadastro_form",
                "email",
            ),
        ]
        self.assertEqual(respostas[0][0].context["next"], next_url)
        self.assertEqual(respostas[1][0].context["next"], next_url)
        for (response, _, _), modal in zip(
            respostas, ("modal-login", "modal-login", "modal-cadastro"), strict=True
        ):
            with self.subTest(modal=modal):
                outro_modal = "modal-cadastro" if modal == "modal-login" else "modal-login"
                self.assertRegex(
                    response.text,
                    rf'<dialog\b[^>]*\bid="{modal}"[^>]*\bdata-auth-open-on-load\b',
                )
                self.assertNotRegex(
                    response.text,
                    rf'<dialog\b[^>]*\bid="{outro_modal}"[^>]*\bdata-auth-open-on-load\b',
                )
        self.assertRedirects(
            self.client.post(login_url, {"username": self.usuario.username, "password": "senha-teste", "next": next_url}),
            next_url,
            fetch_redirect_response=False,
        )
        respostas.append(
            (
                self.client.post(reverse("cadastrar_evento") + filtros, {"nome": "Rascunho"}),
                "evento_form",
                "dataEvento",
            )
        )

        for response, nome_formulario, erro in respostas:
            with self.subTest(nome_formulario=nome_formulario, erro=erro):
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "home/index.html")
                self.assertEqual(response.context["destaque"], self.sabado)
                self.assertEqual(response.context["localidade_selecionada"], "São Paulo|SP")
                form = response.context[nome_formulario]
                self.assertEqual(form.is_bound, erro is not None)
                if erro:
                    self.assertIn(erro, form.errors)
        self.assertEqual(respostas[-1][0].context["evento_form"]["nome"].value(), "Rascunho")
        self.assertFalse(Evento.objects.filter(nome="Rascunho").exists())
