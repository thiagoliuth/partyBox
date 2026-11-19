from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from home.models import Categoria, Evento, Usuario


# Fotos do Unsplash, servidas localmente após o primeiro seed.
# O uso das imagens é permitido pela Unsplash License.
EVENTOS = [
    {
        "nome": "Festival Horizonte: música para ver o sol nascer",
        "descricao": (
            "Uma noite inteira de música brasileira, encontros e pista ao ar livre. "
            "A programação reúne artistas independentes, espaço gastronômico e uma "
            "vista especial do nascer do sol. Chegue cedo para aproveitar os shows "
            "de abertura e traga sua garrafa reutilizável."
        ),
        "categoria": "musica", "dias": 24, "horario": "18:30",
        "cidade": "Belo Horizonte", "estado": "MG", "bairro": "Olhos d'Água",
        "rua": "Rua Gabriela de Melo", "numero": "1250", "pago": True,
        "foto": "festival-horizonte.jpg",
        "url": "https://images.unsplash.com/photo-1506157786151-b8491531f063?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "A Última Estação",
        "descricao": "Uma peça sobre despedidas, recomeços e tudo aquilo que fica por dizer. Após a sessão, haverá conversa com o elenco.",
        "categoria": "teatro", "dias": -18, "horario": "20:00",
        "cidade": "São Paulo", "estado": "SP", "bairro": "Pinheiros",
        "rua": "Rua dos Pinheiros", "numero": "740", "pago": True,
        "foto": "ultima-estacao.jpg",
        "url": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Samba na Praça — edição de domingo",
        "descricao": "Roda de samba aberta, feira de pequenos produtores e atividades para as crianças. Traga a família, os amigos e a cadeira de praia.",
        "categoria": "musica", "dias": 5, "horario": "14:00",
        "cidade": "Rio de Janeiro", "estado": "RJ", "bairro": "Lapa",
        "rua": "Rua do Lavradio", "numero": "100", "pago": False,
        "foto": "samba-praca.jpg",
        "url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Corpo em Movimento: mostra de dança contemporânea",
        "descricao": "Três companhias da região ocupam o palco em uma noite dedicada à dança contemporânea. Classificação livre.",
        "categoria": "danca", "dias": 42, "horario": "19:30",
        "cidade": "Curitiba", "estado": "PR", "bairro": "Centro",
        "rua": "Rua Conselheiro Laurindo", "numero": "280", "pago": True,
        "foto": "corpo-movimento.jpg",
        "url": "https://images.unsplash.com/photo-1504609813442-a8924e83f76e?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Sabores do Cerrado",
        "descricao": "Chefs locais apresentam ingredientes do Cerrado em pratos criados especialmente para esta feira. Degustações, oficina de temperos e música ao vivo.",
        "categoria": "culinaria", "dias": 12, "horario": "11:00",
        "cidade": "Brasília", "estado": "DF", "bairro": "Asa Norte",
        "rua": "Setor de Clubes Esportivos Norte", "numero": "12", "pago": True,
        "foto": "sabores-cerrado.jpg",
        "url": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Corrida das Pontes — 5 km e 10 km",
        "descricao": "Percursos para quem está começando e para quem já treina. Inscrição inclui número de peito, hidratação no trajeto e medalha de participação.",
        "categoria": "esporte", "dias": 31, "horario": "06:30",
        "cidade": "Recife", "estado": "PE", "bairro": "Boa Viagem",
        "rua": "Avenida Boa Viagem", "numero": "2500", "pago": True,
        "foto": "corrida-pontes.jpg",
        "url": "https://images.unsplash.com/photo-1530549387789-4c1017266635?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Ateliês Abertos do Bixiga",
        "descricao": "Um passeio a pé por ateliês, galerias e espaços de criação do bairro. Conheça artistas, veja os processos de perto e descubra trabalhos disponíveis para levar para casa.",
        "categoria": "arte", "dias": -42, "horario": "10:00",
        "cidade": "São Paulo", "estado": "SP", "bairro": "Bela Vista",
        "rua": "Rua Treze de Maio", "numero": "500", "pago": False,
        "foto": "atelies-bixiga.jpg",
        "url": "https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Arraiá da Vila Madalena",
        "descricao": "Bandeirinhas, quadrilha, correio elegante e comidas típicas feitas por cozinhas do bairro. Traga um agasalho e venha dançar.",
        "categoria": "festa", "dias": -9, "horario": "16:00",
        "cidade": "São Paulo", "estado": "SP", "bairro": "Vila Madalena",
        "rua": "Rua Aspicuelta", "numero": "300", "pago": False,
        "foto": "arraia-vila.jpg",
        "url": "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Frequência — noite de música eletrônica",
        "descricao": "DJs da cena local ocupam a pista em uma noite de house e techno. Entrada permitida somente para maiores de 18 anos.",
        "categoria": "rave", "dias": 19, "horario": "22:00",
        "cidade": "Florianópolis", "estado": "SC", "bairro": "Centro",
        "rua": "Avenida Paulo Fontes", "numero": "800", "pago": True,
        "foto": "frequencia.jpg",
        "url": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Cinema na laje: curtas brasileiros",
        "descricao": "Sessão gratuita de curtas-metragens brasileiros, com bate-papo ao fim da exibição. A projeção acontece ao ar livre; em caso de chuva, será transferida para o salão.",
        "categoria": "arte", "dias": 2, "horario": "19:00",
        "cidade": "Salvador", "estado": "BA", "bairro": "Santo Antônio Além do Carmo",
        "rua": "Rua Direita de Santo Antônio", "numero": "80", "pago": False,
        "foto": "cinema-laje.jpg",
        "url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Pedal de sábado: parque e café",
        "descricao": "Pedal leve de 18 km, com saída em grupo e parada para café. Capacete obrigatório; recomendado levar água e revisar a bicicleta antes do passeio.",
        "categoria": "esporte", "dias": 9, "horario": "07:00",
        "cidade": "Porto Alegre", "estado": "RS", "bairro": "Moinhos de Vento",
        "rua": "Rua Padre Chagas", "numero": "120", "pago": False,
        "foto": "pedal-sabado.jpg",
        "url": "https://images.unsplash.com/photo-1517649763962-0c623066013b?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Feira de Cerâmica e Café",
        "descricao": "Peças autorais, café passado na hora e conversa com quem faz. Uma manhã para conhecer a produção ceramista da cidade e apoiar os pequenos ateliês.",
        "categoria": "arte", "dias": -3, "horario": "09:30",
        "cidade": "Ouro Preto", "estado": "MG", "bairro": "Pilar",
        "rua": "Rua do Pilar", "numero": "45", "pago": False,
        "foto": "ceramica-cafe.jpg",
        "url": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Jantar de quintal: cozinha mineira",
        "descricao": "Menu sazonal de cinco etapas preparado com ingredientes de produtores locais. O valor inclui jantar completo; bebidas cobradas à parte. Lugares limitados.",
        "categoria": "culinaria", "dias": 55, "horario": "19:30",
        "cidade": "Ouro Preto", "estado": "MG", "bairro": "Rosário",
        "rua": "Rua Getúlio Vargas", "numero": "215", "pago": True,
        "foto": "jantar-quintal.jpg",
        "url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=1400&q=82",
    },
    {
        "nome": "Roda de choro no Mercado",
        "descricao": "Músicos convidados resgatam clássicos do choro e recebem participações espontâneas. O evento acontece na praça de alimentação do mercado.",
        "categoria": "musica", "dias": -28, "horario": "12:00",
        "cidade": "Belém", "estado": "PA", "bairro": "Campina",
        "rua": "Boulevard Castilhos França", "numero": "100", "pago": False,
        "sem_foto": True,
    },
    {
        "nome": "Pequenos Inventores — oficina de arte para crianças",
        "descricao": "Uma tarde para experimentar cores, materiais recicláveis e ideias malucas. Oficina conduzida por educadores; crianças devem estar acompanhadas por uma pessoa responsável.",
        "categoria": "arte", "dias": 16, "horario": "15:00",
        "cidade": "Campinas", "estado": "SP", "bairro": "Cambuí",
        "rua": "Rua Coronel Quirino", "numero": "900", "pago": True,
        "sem_foto": True,
    },
    {
        "nome": "Baile de máscaras do centro",
        "descricao": "Uma festa para celebrar a cidade com DJs, bar local e concurso de máscaras. Fantasias são bem-vindas, mas não obrigatórias.",
        "categoria": "festa", "dias": 68, "horario": "21:30",
        "cidade": "Fortaleza", "estado": "CE", "bairro": "Centro",
        "rua": "Rua dos Tabajaras", "numero": "500", "pago": True,
        "sem_foto": True,
    },
]


class Command(BaseCommand):
    help = "Acrescenta eventos fictícios e capas locais para visualizar a aplicação."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="thalles", help="Usuário dono de parte dos eventos (padrão: thalles).")

    def handle(self, *args, **options):
        try:
            dono = Usuario.objects.get(username=options["username"])
        except Usuario.DoesNotExist as exc:
            raise CommandError(
                f"Usuário '{options['username']}' não encontrado. "
                "Informe a conta existente com --username."
            ) from exc

        categorias = {
            categoria.tipo: categoria
            for categoria in (
                Categoria.objects.get_or_create(tipo=tipo)[0]
                for tipo, _ in Categoria.CategoriaType.choices
            )
        }
        imagens_novas = 0
        eventos_novos = 0
        hoje = date.today()

        for indice, dados in enumerate(EVENTOS):
            imagem = None
            if not dados.get("sem_foto"):
                pasta = settings.MEDIA_ROOT / "demo-eventos"
                pasta.mkdir(parents=True, exist_ok=True)
                destino = pasta / dados["foto"]
                if not destino.exists():
                    requisicao = Request(dados["url"], headers={"User-Agent": "PartyBoxd-demo-seed/1.0"})
                    try:
                        with urlopen(requisicao, timeout=30) as resposta:
                            conteudo = resposta.read()
                    except Exception as exc:
                        raise CommandError(f"Falha ao baixar a capa {dados['foto']}: {exc}") from exc
                    if not conteudo.startswith(b"\xff\xd8\xff"):
                        raise CommandError(f"A URL da capa {dados['foto']} não retornou JPEG.")
                    destino.write_bytes(conteudo)
                    imagens_novas += 1
                imagem = Path("demo-eventos") / dados["foto"]

            defaults = {
                "descricao": dados["descricao"],
                "dataEvento": hoje + timedelta(days=dados["dias"]),
                "horarioEvento": dados["horario"],
                "siglaEstado": dados["estado"],
                "cidade": dados["cidade"],
                "bairro": dados["bairro"],
                "rua": dados["rua"],
                "numero": dados["numero"],
                "categoria": categorias[dados["categoria"]],
                "ehPago": dados["pago"],
                "ehPublico": True,
                "usuario": dono if indice < 6 else Usuario.objects.order_by("pk").exclude(pk=dono.pk).first() or dono,
            }
            evento, criado = Evento.objects.get_or_create(nome=dados["nome"], defaults=defaults)
            if criado:
                eventos_novos += 1
                if imagem:
                    evento.thumbnail.name = str(imagem)
                    evento.save(update_fields=["thumbnail"])

        self.stdout.write(self.style.SUCCESS(
            f"Seed concluído: {eventos_novos} eventos novos, "
            f"{len(Categoria.CategoriaType.choices)} categorias disponíveis e "
            f"{imagens_novas} capas baixadas. Reexecuções não duplicam eventos."
        ))
