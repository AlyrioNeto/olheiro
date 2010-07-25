#!/usr/bin/python

import itertools
import pickle
import bz2
import json

import mechanize


LOGIN_URL = 'https://loginfree.globo.com/login/438'
URL_MERCADO = ('http://cartolafc.globo.com/mercado/filtrar.json?'
               'page=%d&order_by=preco&status_id=7')
MERCADO_DUMP = './mercado.dump'
MERCADO_TXT= './mercado.txt'


class Cenario:
    def __init__(self):
        self.clubes = []
        self.jogadores = []
        self.partidas = []

    def get_clube_by_id(self, id_):
        candidates = [clube
                      for clube in self.clubes
                      if clube.id == id_]
        if candidates:
            return candidates[0]
        else:
            return None

    def get_partida_by_id(self, id_):
        candidates = [partida
                      for partida in self.partidas
                      if partida.id == id_]
        if candidates:
            return candidates[0]
        else:
            return None

    def add_clube(self, clube):
        if clube.id not in (x.id for x in self.clubes):
            self.clubes.append(clube)
        return self.get_clube_by_id(clube.id)

    def add_partida(self, partida):
        if partida.id not in (x.id for x in self.partidas):
            self.partidas.append(partida)
        return self.get_partida_by_id(partida.id)


class Clube:
    def __init__(self, data):
        self.id = data['id']
        self.abreviacao = data['abreviacao']
        self.mercado = data['mercado']
        self.nome = data['nome']
        self.slug = data['slug']

    def __repr__(self):
        return '<Clube %s, %s>' % (self.id,
                                   self.abreviacao)


class ScoutTable:
    SCOUTS = ['RB', 'FC', 'GC', 'CA', 'CV', 'SG', 'DD', 'DP', 'GS',
              'FS', 'PE', 'A', 'FT', 'FD', 'FF', 'G', 'I', 'PP']
    PONTUACAO = {'RB': 1.7, 'FC': -0.5, 'GC': -6, 'CA': -2, 'CV': -5,
                 'SG': 5, 'DD': 3, 'DP': 7, 'GS': -2, 'FS': 0.5,
                 'PE': -0.3, 'A': 5, 'FT': 3.5, 'FD': 1, 'FF': 0.7,
                 'G': 8, 'I': -0.5, 'PP': -3.5}

    def __init__(self, data):
        self.conteudo = {}
        for item in data:
            self.conteudo[item['nome']] = item['quantidade']

    def get_scout(self, scout):
        if scout in ScoutTable.SCOUTS:
            return self.conteudo.get(scout, 0)
        return None

    def pontuacao(self):
        soma = 0.0
        return soma

    def imprime(self):
        elementos = []
        for scout in ScoutTable.SCOUTS:
            elementos.append(str(self.get_scout(scout)))
        return '\t'.join(elementos)


class Partida:
    def __init__(self, data):
        self.id_clube_casa = data['partida_clube_casa']['id']
        self.id_clube_visitante = data['partida_clube_visitante']['id']
        self.quando = data['partida_data']
        self.id = (self.id_clube_casa,
                   self.id_clube_visitante,
                   self.quando)

    def __repr__(self):
        return '<Partida %s>' % std(self.id)


class Jogador:
    def __init__(self, data, cenario):
        self.id = data['id']
        self.apelido = data['apelido']
        clube = Clube(data['clube'])
        cenario.add_clube(clube)
        self.clube = clube
        self.posicao = data['posicao']['abreviacao']
        self.jogos = int(data['jogos'])
        self.preco = float(data['preco'])
        self.variacao = float(data['variacao'])
        self.media = float(data['media'])
        self.pontos = float(data['pontos'])
        self.scout = ScoutTable(data['scout'])

    def imprime(self):
        elementos = []
        elementos.append(str(self.id))
        elementos.append(self.apelido)
        elementos.append(self.clube.abreviacao)
        elementos.append(self.posicao)
        elementos.append('%d' % self.jogos)
        elementos.append('%.2f' % self.preco)
        elementos.append('%.2f' % self.variacao)
        elementos.append('%.2f' % self.media)
        elementos.append('%.2f' % self.pontos)
        elementos.append(self.scout.imprime())
        return '\t'.join(elementos)

    def __repr__(self):
        return '<Jogador %s, %s, %s>' % (str(self.id),
                                         self.apelido.encode('iso-8859-1'),
                                         repr(self.clube))


def atualiza_mercado():
    paginas = []

    try:
        with open(MERCADO_DUMP, 'r') as f:
            paginas.extend(pickle.load(f))
        print 'Cache de mercado encontrado.'
    except IOError:
        print 'Cache de mercado nao encontrado...'

        br = mechanize.Browser()

        try:
            from settings import USERNAME
            from settings import COMPRESSED_PASSWORD
            print "Arquivo 'settings.py' encontrado."
        except ImportError:
            from getpass import getpass
            print "Arquivo 'settings.py' nao encontrado..."
            print 'Entre com o login e a senha do Cartola FC.'
            USERNAME = raw_input(' - Login: ')
            COMPRESSED_PASSWORD = bz2.compress(getpass(' - Senha: '))

        print 'Iniciando download das informacoes de mercado...'

        br.open(LOGIN_URL)
        br.select_form(nr=0)
        br['login-passaporte'] = USERNAME
        br['senha-passaporte'] = bz2.decompress(COMPRESSED_PASSWORD)

        r_login = br.submit()
        conteudo = r_login.get_data()

        for n in itertools.count(1):
            r_mercado = br.open(URL_MERCADO % n)
            pagina = str(r_mercado.get_data())
            paginas.append(pagina)
            data = json.JSONDecoder().decode(pagina)
            if data['page']['atual'] == data['page']['total']:
                break

        print 'Download concluido.'

        f = open(MERCADO_DUMP, 'w')
        pickle.dump(paginas, f)
        f.close()

    mercado = []
    for pagina in paginas:
        data = json.JSONDecoder().decode(pagina)
        mercado.extend(data[u'atleta'])

    cenario = Cenario()
    for item in mercado:
        cenario.jogadores.append(Jogador(item, cenario))
        cenario.add_partida(Partida(item))

    return cenario


if __name__ == '__main__':
    cenario = atualiza_mercado()

    f = open(MERCADO_TXT, 'w')
    for jogador in cenario.jogadores:
        f.write(jogador.imprime().encode('iso-8859-1')+'\n')
    f.close()
