#!/usr/bin/env python3
"""!
@file build_mascot.py
@brief Gera os sprites em pixel art do mascote do IAPet.

O mascote é um elefante humanoide no arquétipo de monge/sábio (inspirado nos
"loxodontes" da fantasia): ereto, de manto com detalhes dourados, presas,
olhos pequenos sob sobrolho pesado e um cajado com uma gema. A cor da gema é
definida por estado do assistente e serve como indicador visual principal.

Os quadros são compostos por partes (manto, braços, cajado, orelhas, cabeça,
presas, tromba, olhos) sobre uma grade W x H indexada por uma paleta de 16
cores. Saídas:
  - firmware/M5_IAPet/src/mascot_data.h / mascot_data.cpp: paleta RGB565,
    quadros 4 bpp em PROGMEM e animações por estado (com as cores da gema);
  - media/mascot/preview.png: folha de revisão (uma linha por estado).

Sem dependências externas (PNG escrito com zlib/struct).
Uso: python3 tools/mascot/build_mascot.py
"""

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW_SRC = ROOT / "firmware" / "M5_IAPet" / "src"
PREVIEW_DIR = ROOT / "media" / "mascot"

W = 36
FIG_AXIS = 31  # x espelhado = FIG_AXIS - x (figura centrada em x = 15.5)
H = 40

# Paleta: caractere -> (índice, RGB888). Índice 0 é o fundo da UI.
# Os índices da gema (J/j) são sobrescritos por estado (ver ANIMS).
PALETTE = {
    ".": (0, (0x10, 0x12, 0x1C)),   # fundo
    "K": (1, (0x1C, 0x1A, 0x22)),   # contorno
    "G": (2, (0x8C, 0x90, 0x9C)),   # pele
    "g": (3, (0x62, 0x66, 0x74)),   # pele sombra / rugas / sobrolho
    "L": (4, (0xB0, 0xB4, 0xBE)),   # pele luz
    "W": (5, (0xFA, 0xF6, 0xEA)),   # marfim (presas)
    "E": (6, (0x0C, 0x0A, 0x0A)),   # olho
    "M": (7, (0xE4, 0xD8, 0xBC)),   # manto (creme)
    "m": (8, (0xB4, 0xA4, 0x84)),   # manto sombra
    "Y": (9, (0xD8, 0xA8, 0x3C)),   # ouro
    "y": (10, (0x9A, 0x70, 0x22)),  # ouro sombra
    "J": (11, (0x6A, 0x8C, 0x9A)),  # gema (núcleo) — por estado
    "j": (12, (0x2A, 0x3A, 0x44)),  # gema (brilho) — por estado
    "n": (13, (0x5A, 0x44, 0x30)),  # túnica interna
    "T": (14, (0x7A, 0x52, 0x30)),  # madeira do cajado
    "w": (15, (0xF8, 0xF8, 0xF8)),  # branco do olho / brilho
}
GEM_CORE_INDEX = PALETTE["J"][0]
GEM_GLOW_INDEX = PALETTE["j"][0]

# --- olhos ----------------------------------------------------------------
# Cada olho: esclera 5x3 ('w') com pupila 2x2 ('E') que se desloca, pálpebra
# e sobrolho. A pupila NÃO é espelhada (os dois olhos olham para o mesmo
# lado); o sobrolho é espelhado (expressão simétrica).

SCLERA = [".www.", "wwwww", ".www."]
EYE_LEFT_X = 10    # coluna do olho esquerdo (o direito é espelhado)
EYE_Y = 7          # linha superior da esclera

# Posição (coluna, linha) da pupila dentro da esclera, por olho (esq., dir.).
# "c" converge levemente: o mascote olha para quem está na frente da tela.
GAZE = {
    "c":  ((1, 1), (2, 1)),
    "l":  ((0, 1), (0, 1)),
    "r":  ((3, 1), (3, 1)),
    "u":  ((1, 0), (2, 0)),
    "ul": ((0, 0), (0, 0)),
    "ur": ((3, 0), (3, 0)),
}

# Sobrolho do olho esquerdo: linhas EYE_Y-2 e EYE_Y-1.
BROWS = {
    "neutral": [".....", "ggggg"],
    "raised":  ["ggggg", "....."],
    "sad":     ["...gg", "ggg.."],
    "focus":   ["gg...", "..ggg"],
}

# Pálpebras: linhas da esclera cobertas por pele ou fechadas.
LIDS = ("open", "half", "smile", "closed")

# --- poses ----------------------------------------------------------------

EARS = {  # orelha esquerda: centro, raios; a direita é espelhada
    "normal": ((6.5, 13.0), 4.6, 7.0),
    "wide":   ((5.0, 11.5), 5.2, 7.8),
    "droop":  ((7.0, 15.0), 4.2, 7.0),
}

TRUNKS = {  # polilinha da base (entre os olhos) à ponta
    "down": [(16, 12), (16, 18), (16, 24), (16.8, 27), (18.8, 27.5)],
    "sway": [(16, 12), (16, 18), (15.8, 24), (15, 27), (13, 27.5)],
    "lift": [(16, 12), (16, 18), (16.8, 23), (19.5, 24), (21, 21.5)],
    "limp": [(16, 12), (16, 18), (16, 24), (16, 29)],
}


def ellipse(cx, cy, rx, ry):
    """!
    @brief Rasteriza uma elipse preenchida.

    @param cx Centro X em pixels (aceita fração).
    @param cy Centro Y em pixels (aceita fração).
    @param rx Raio horizontal em pixels.
    @param ry Raio vertical em pixels.
    @return Conjunto de coordenadas (x, y) cujos centros caem dentro da elipse,
            recortado à grade W x H.
    """
    pts = set()
    for y in range(H):
        for x in range(W):
            dx = (x + 0.5 - cx) / rx
            dy = (y + 0.5 - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                pts.add((x, y))
    return pts


def polygon(points):
    """!
    @brief Rasteriza um polígono preenchido (regra par-ímpar).

    @param points Lista de vértices (x, y) em pixels, em ordem.
    @return Conjunto de coordenadas (x, y) cujos centros caem dentro.
    """
    pts = set()
    n = len(points)
    for y in range(H):
        py = y + 0.5
        for x in range(W):
            px = x + 0.5
            inside = False
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 > py) != (y1 > py):
                    if px < x0 + (py - y0) * (x1 - x0) / (y1 - y0):
                        inside = not inside
            if inside:
                pts.add((x, y))
    return pts


def thick_path(points, radius, tip_radius=None):
    """!
    @brief Rasteriza uma polilinha espessa (tromba, presas, braços).

    @param points     Lista de vértices (x, y) em pixels, da base à ponta.
    @param radius     Raio do traço ao longo do caminho, em pixels.
    @param tip_radius Raio do disco na ponta, ou None para usar @p radius.
    @return Conjunto de coordenadas (x, y) cobertas pelo traço.
    """
    samples = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(1, int(math.hypot(x1 - x0, y1 - y0) * 4))
        for i in range(steps):
            t = i / steps
            samples.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, radius))
    end_r = radius if tip_radius is None else tip_radius
    samples.append((points[-1][0], points[-1][1], end_r))
    pts = set()
    for y in range(H):
        for x in range(W):
            for sx, sy, r in samples:
                if (x + 0.5 - sx) ** 2 + (y + 0.5 - sy) ** 2 <= r * r:
                    pts.add((x, y))
                    break
    return pts


def mirror(mask):
    """!
    @brief Espelha uma máscara no eixo vertical da figura.

    @param mask Conjunto de coordenadas (x, y).
    @return Novo conjunto com x substituído por FIG_AXIS - x.
    """
    return {(FIG_AXIS - x, y) for x, y in mask}


def mirror_patch(patch):
    """!
    @brief Espelha horizontalmente um patch ASCII.

    @param patch Lista de strings de mesma largura.
    @return Nova lista com cada linha invertida.
    """
    return [row[::-1] for row in patch]


def draw_part(grid, mask, fill, shade=None, light=None):
    """!
    @brief Desenha uma parte com contorno de 1 px, sombra e luz.

    Pixels da máscara com algum vizinho-4 fora dela viram contorno ('K').
    Entre os internos, os que estão a 1 px do contorno inferior/direito
    recebem @p shade, e os a 1 px do contorno superior/esquerdo recebem
    @p light; os demais recebem @p fill.

    @param grid  Grade H x W de caracteres da paleta, alterada in-place.
    @param mask  Conjunto de coordenadas (x, y) da parte.
    @param fill  Caractere de preenchimento.
    @param shade Caractere de sombra, ou None para não sombrear.
    @param light Caractere de luz, ou None para não iluminar.
    @return None.
    """
    for x, y in mask:
        if not (0 <= x < W and 0 <= y < H):
            continue
        edge = any((x + dx, y + dy) not in mask
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            grid[y][x] = "K"
        elif shade and ((x, y + 2) not in mask or (x + 2, y) not in mask):
            grid[y][x] = shade
        elif light and ((x, y - 2) not in mask or (x - 2, y) not in mask):
            grid[y][x] = light
        else:
            grid[y][x] = fill


def stamp(grid, patch, ox, oy):
    """!
    @brief Copia um patch ASCII para a grade, ignorando pixels '.'.

    @param grid  Grade H x W de caracteres da paleta, alterada in-place.
    @param patch Lista de strings de mesma largura.
    @param ox    Coluna de destino do canto superior esquerdo.
    @param oy    Linha de destino do canto superior esquerdo.
    @return None.
    """
    for dy, row in enumerate(patch):
        for dx, ch in enumerate(row):
            x, y = ox + dx, oy + dy
            if ch != "." and 0 <= x < W and 0 <= y < H:
                grid[y][x] = ch


def draw_eye(grid, ox, gaze, lid, brow):
    """!
    @brief Desenha um olho (esclera, pupila, pálpebra) e o sobrolho.

    @param grid Grade H x W de caracteres da paleta, alterada in-place.
    @param ox   Coluna esquerda da esclera.
    @param gaze Tupla (coluna, linha) da pupila dentro da esclera.
    @param lid  Pálpebra: "open", "half" (linha de cima coberta), "smile"
                (linha de baixo coberta) ou "closed".
    @param brow Lista de 2 strings com o sobrolho (linhas EYE_Y-2, EYE_Y-1).
    @return None.
    """
    stamp(grid, brow, ox, EYE_Y - 2)
    if lid == "closed":
        stamp(grid, [".KKK."], ox, EYE_Y + 1)
        return
    stamp(grid, SCLERA, ox, EYE_Y)
    gx, gy = gaze
    for dy in range(2):
        for dx in range(2):
            px, py = gx + dx, gy + dy
            if SCLERA[py][px] == "w":
                grid[EYE_Y + py][ox + px] = "E"
    if lid == "half":
        stamp(grid, ["ggggg"], ox, EYE_Y)
    elif lid == "smile":
        stamp(grid, [".GGG."], ox, EYE_Y + 2)


BOOK_CLOSED = [  # em pé, capa de frente; '*' = emblema (gema quando aceso)
    "KKKKKK",
    "KnTTTK",
    "KnTTTK",
    "KnTYTK",
    "KnY*YK",
    "KnTYTK",
    "KnTTTK",
    "KnTTTK",
    "KKKKKK",
]
BOOK_CLOSED_POS = (3, 27)

BOOK_OPEN = [  # aberto, páginas voltadas para fora
    ".KKKK.KKKK.",
    "KwwwwKwwwwK",
    "KwmmwKwmmwK",
    "KwwwwKwwwwK",
    "KwmmwKwmmwK",
    "KTTTTTTTTTK",
    ".KKKKKKKKK.",
]
BOOK_OPEN_POS = (3, 23)

BOOK_FLIP = [  # aberto com a página da direita virando (borda curva)
    ".KKKK.KKKK.",
    "KwwwwKKwwwK",
    "KwmmwKwKwwK",
    "KwwwwKwwKwK",
    "KwmmwKwwwKK",
    "KTTTTTTTTTK",
    ".KKKKKKKKK.",
]


def draw_book(grid, mode, lit, halo):
    """!
    @brief Desenha o livro (sem o braço/mão, desenhados depois por cima).

    @param grid Grade H x W de caracteres da paleta, alterada in-place.
    @param mode "closed" (fechado, em pé), "open" (aberto) ou "flip"
                (aberto com uma página virando).
    @param lit  True para acender o livro com a cor da gema: emblema da capa
                (fechado) ou páginas (aberto).
    @param halo True para desenhar o halo de brilho em volta do livro.
    @return None.
    """
    if mode == "closed":
        patch, (ox, oy) = BOOK_CLOSED, BOOK_CLOSED_POS
        swap = {"*": "J" if lit else "Y"}
    else:
        patch = BOOK_FLIP if mode == "flip" else BOOK_OPEN
        ox, oy = BOOK_OPEN_POS
        swap = {"w": "J", "m": "w"} if lit else {}
    if halo:
        bw, bh = len(patch[0]), len(patch)
        for x, y in ellipse(ox + bw / 2, oy + bh / 2, bw / 2 + 2.2, bh / 2 + 2.2):
            if grid[y][x] in ".Mmn":
                grid[y][x] = "j"
    stamp(grid, ["".join(swap.get(ch, ch) for ch in row) for row in patch], ox, oy)


def compose(ears="normal", trunk="down", gaze="c", lid="open",
            brow="neutral", glow=False, book="closed", book_lit=False):
    """!
    @brief Monta um quadro completo do mascote a partir das partes.

    @param ears  Pose das orelhas: chave de EARS.
    @param trunk Pose da tromba: chave de TRUNKS.
    @param gaze  Direção do olhar: chave de GAZE.
    @param lid   Pálpebras: um de LIDS.
    @param brow  Sobrolho: chave de BROWS.
    @param glow  True para desenhar o halo de brilho da gema (e do livro,
                 se @p book_lit).
    @param book  Livro: "closed", "open" ou "flip" (ver draw_book()).
    @param book_lit True para o livro brilhar com a cor da gema.
    @return Grade H x W (lista de listas) de caracteres da paleta.
    """
    grid = [["."] * W for _ in range(H)]

    # Manto: ombros largos e curvados + saia trapezoidal até a base.
    robe = polygon([(5.5, 23), (26.5, 23), (28, 40), (4, 40)])
    robe |= ellipse(16, 24, 10.8, 5.0)
    draw_part(grid, robe, "M", "m")
    # Abertura em V com debrum dourado e túnica interna mais escura.
    for y in range(21, H):
        half = 1.5 + (y - 21) * 0.18
        xl, xr = int(round(16 - half)), int(round(15 + half))
        for x in range(xl + 1, xr):
            grid[y][x] = "n"
        grid[y][xl] = "Y"
        grid[y][xr] = "Y"
    stamp(grid, ["K" * 16], 8, 31)  # faixa na cintura
    stamp(grid, ["Y" * 16], 8, 32)
    stamp(grid, ["y" * 16], 8, 33)
    stamp(grid, ["K" * 16], 8, 34)

    # Braço livre com o livro: fechado junto ao quadril ou aberto no peito.
    if book == "closed":
        arm, hand = [(8, 24), (7, 28), (7.5, 30)], (8.5, 31.0)
    else:
        arm, hand = [(8, 23), (6.5, 26.5), (7, 29)], (8.0, 29.5)
    draw_part(grid, thick_path(arm, 2.5), "M", "m")
    draw_book(grid, book, book_lit, glow and book_lit)
    draw_part(grid, ellipse(hand[0], hand[1], 2.0, 2.0), "G", "g")

    # Cajado à direita (2 px de madeira, sem contorno), gema no topo.
    for y in range(7, H):
        stamp(grid, ["KTTK"], 27, y)
    if glow:
        for x, y in ellipse(29, 5, 4.4, 4.4):
            if grid[y][x] == ".":
                grid[y][x] = "j"
    stamp(grid, ["yY..Yy", ".yYYy."], 26, 6)  # engaste dourado
    draw_part(grid, ellipse(29, 4.5, 2.6, 2.8), "J")
    stamp(grid, ["w"], 28, 3)

    # Braço direito segurando o cajado.
    draw_part(grid, thick_path([(23, 23), (25.5, 25), (27, 26)], 2.5), "M", "m")
    draw_part(grid, ellipse(28.5, 26.5, 2.0, 2.0), "G", "g")

    # Gola dourada.
    stamp(grid, ["..yYYYYYYYYYYy..", ".yY..........Yy."], 8, 20)

    # Orelhas grandes, caídas ao lado da cabeça.
    (ecx, ecy), erx, ery = EARS[ears]
    ear = ellipse(ecx, ecy, erx, ery)
    inner = ellipse(ecx + 0.6, ecy - 0.2, erx - 1.8, ery - 2.2)
    for m_ear, m_inner in ((ear, inner), (mirror(ear), mirror(inner))):
        draw_part(grid, m_ear, "G", "g", "L")
        for x, y in m_inner:
            if grid[y][x] != "K":
                grid[y][x] = "g"

    # Cabeça em cúpula, com testa iluminada e adorno dourado.
    draw_part(grid, ellipse(16, 10, 7.2, 7.8), "G", "g", "L")
    stamp(grid, [".Y.", "YyY", ".Y."], 15, 2)

    # Presas de marfim curvando para fora (antes da tromba).
    tusk_l = thick_path([(13.5, 14), (11.5, 16.5), (10.6, 19), (11.2, 21.2)], 1.55)
    draw_part(grid, tusk_l, "W")
    draw_part(grid, mirror(tusk_l), "W")

    # Tromba longa com rugas.
    path = TRUNKS[trunk]
    t_mask = thick_path(path, 1.9, 2.1)
    draw_part(grid, t_mask, "G", "g")
    for y in (13, 16, 19, 22):
        for x in range(W):
            if (x, y) in t_mask and grid[y][x] in "GL" and abs(x + 0.5 - 16) < 1.5:
                grid[y][x] = "g"

    # Olhos: pupila com a mesma direção nos dois, sobrolho espelhado.
    gaze_l, gaze_r = GAZE[gaze]
    right_x = FIG_AXIS - (EYE_LEFT_X + len(SCLERA[0]) - 1)
    draw_eye(grid, EYE_LEFT_X, gaze_l, lid, BROWS[brow])
    draw_eye(grid, right_x, gaze_r, lid, mirror_patch(BROWS[brow]))

    return grid


# Quadros nomeados (ordem = índice no firmware).
# Consultar o livro = olhar para a esquerda (de quem vê) com pálpebra baixa.
READ = dict(book="open", gaze="l", lid="half")
FRAMES = {
    "idle_c":        dict(),
    "idle_blink":    dict(lid="closed"),
    "idle_l":        dict(gaze="l"),
    "idle_r":        dict(gaze="r"),
    "idle_sway":     dict(trunk="sway", gaze="l", lid="half"),
    "listen_read_a": dict(READ, ears="wide", glow=True),
    "listen_read_b": dict(READ, ears="normal"),
    "listen_look_a": dict(book="open", ears="wide", brow="raised", glow=True),
    "listen_look_b": dict(book="open", ears="normal", brow="raised"),
    "think_read":    dict(READ, brow="focus", glow=True),
    "think_flip":    dict(READ, book="flip", brow="focus"),
    "think_up":      dict(book="open", gaze="ur", brow="focus", glow=True),
    "think_closed":  dict(book="open", lid="closed", brow="focus"),
    "answer_a":      dict(book="open", book_lit=True, trunk="lift",
                          lid="smile", glow=True),
    "answer_b":      dict(book="open", book_lit=True, trunk="down",
                          lid="smile"),
    "error_a":       dict(book_lit=True, ears="droop", trunk="limp", gaze="l",
                          lid="half", brow="sad", glow=True),
    "error_b":       dict(book_lit=True, ears="droop", trunk="limp", gaze="r",
                          lid="half", brow="sad"),
}

# Animações por estado: cores da gema (núcleo, brilho) e passos (quadro, ms).
ANIMS = {
    "IDLE": dict(
        gem=((0x6A, 0x8C, 0x9A), (0x2A, 0x3A, 0x44)),
        steps=[("idle_c", 1800), ("idle_blink", 120), ("idle_c", 900),
               ("idle_l", 700), ("idle_c", 300), ("idle_r", 700),
               ("idle_c", 1200), ("idle_sway", 800), ("idle_c", 400)]),
    "LISTENING": dict(
        gem=((0x6C, 0xC8, 0xFF), (0x24, 0x5C, 0x8A)),
        steps=[("listen_read_a", 450), ("listen_read_b", 450),
               ("listen_look_a", 450), ("listen_look_b", 450)]),
    "THINKING": dict(
        gem=((0xFF, 0xD8, 0x5A), (0x7A, 0x5E, 0x1A)),
        steps=[("think_read", 700), ("think_flip", 250), ("think_read", 500),
               ("think_up", 700), ("think_closed", 800)]),
    "ANSWER": dict(
        gem=((0x8C, 0xF0, 0x9C), (0x2A, 0x70, 0x3A)),
        steps=[("answer_a", 600), ("answer_b", 600)]),
    "ERROR": dict(
        gem=((0xFF, 0x60, 0x60), (0x80, 0x24, 0x24)),
        steps=[("error_a", 450), ("error_b", 450)]),
}


def rgb565(rgb):
    """!
    @brief Converte uma cor RGB888 para RGB565.

    @param rgb Tupla (r, g, b) com componentes 0-255.
    @return Inteiro de 16 bits no formato RGB565.
    """
    r, g, b = rgb
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def pack_4bpp(grid):
    """!
    @brief Empacota um quadro em 4 bits por pixel (2 pixels por byte).

    @param grid Grade H x W de caracteres da paleta.
    @return bytes com H*W/2 bytes; nibble alto = pixel da esquerda.
    """
    out = bytearray()
    for row in grid:
        idx = [PALETTE[ch][0] for ch in row]
        for i in range(0, W, 2):
            out.append((idx[i] << 4) | idx[i + 1])
    return bytes(out)


def write_png(path, pixels):
    """!
    @brief Grava uma imagem RGB 8 bits em PNG sem dependências externas.

    @param path   Caminho do arquivo de saída.
    @param pixels Lista de linhas; cada linha é uma lista de tuplas (r, g, b).
    @return None.
    """
    height, width = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px)
                   for row in pixels)

    def chunk(tag, data):
        """!
        @brief Monta um chunk PNG (tamanho, tipo, dados, CRC).

        @param tag  Tipo do chunk, 4 bytes ASCII (ex.: b"IHDR").
        @param data Conteúdo do chunk.
        @return bytes do chunk serializado.
        """
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def build_preview(grids, scale=5, gap=8):
    """!
    @brief Gera a folha de revisão: uma linha por estado, com a gema na cor
           do estado.

    @param grids Dicionário nome do quadro -> grade.
    @param scale Fator de ampliação de cada pixel.
    @param gap   Espaço em pixels entre quadros.
    @return None (grava media/mascot/preview.png).
    """
    rows = []
    for anim in ANIMS.values():
        names = []
        for name, _ in anim["steps"]:
            if name not in names:
                names.append(name)
        rows.append((names, anim["gem"]))
    cols = max(len(names) for names, _ in rows)
    cw, ch_ = W * scale, H * scale
    width = gap + cols * (cw + gap)
    height = gap + len(rows) * (ch_ + gap)
    border = (0x3A, 0x3E, 0x55)
    pixels = [[border] * width for _ in range(height)]
    for r, (names, (core, glow)) in enumerate(rows):
        colors = {ch: rgb for ch, (_, rgb) in PALETTE.items()}
        colors["J"], colors["j"] = core, glow
        for c, name in enumerate(names):
            ox = gap + c * (cw + gap)
            oy = gap + r * (ch_ + gap)
            for y in range(ch_):
                for x in range(cw):
                    pixels[oy + y][ox + x] = colors[grids[name][y // scale][x // scale]]
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    write_png(PREVIEW_DIR / "preview.png", pixels)


def write_firmware(grids):
    """!
    @brief Gera mascot_data.h/.cpp com paleta, quadros e animações.

    @param grids Dicionário nome do quadro -> grade, na ordem de FRAMES.
    @return None (grava os arquivos em firmware/M5_IAPet/src/).
    """
    names = list(grids)
    banner = "// GERADO por tools/mascot/build_mascot.py — não editar à mão.\n"

    h = [banner, "#pragma once\n", "#include <Arduino.h>\n\n",
         f"#define MASCOT_W {W}\n", f"#define MASCOT_H {H}\n",
         f"#define MASCOT_FRAME_BYTES {W * H // 2}\n",
         f"#define MASCOT_AXIS_X {(FIG_AXIS + 1) // 2}  ///< coluna do eixo da figura\n",
         "#define MASCOT_PALETTE_SIZE 16\n",
         f"#define MASCOT_GEM_CORE_INDEX {GEM_CORE_INDEX}  ///< cor por estado\n",
         f"#define MASCOT_GEM_GLOW_INDEX {GEM_GLOW_INDEX}  ///< cor por estado\n\n",
         "/** @brief Um passo de animação: quadro exibido e duração. */\n",
         "typedef struct {\n  uint8_t frame;  ///< índice em mascot_frames\n"
         "  uint16_t ms;    ///< duração do quadro em ms\n} mascot_step_t;\n\n",
         "/** @brief Animação em loop de um estado, com as cores da gema. */\n",
         "typedef struct {\n  const mascot_step_t* steps;  ///< passos\n"
         "  uint8_t count;               ///< quantidade de passos\n"
         "  uint16_t gem_core;           ///< RGB565 do núcleo da gema\n"
         "  uint16_t gem_glow;           ///< RGB565 do halo da gema\n"
         "} mascot_anim_t;\n\n",
         "/** @brief Índices dos quadros em mascot_frames. */\n",
         "enum mascot_frame_id : uint8_t {\n"]
    h += [f"  MASCOT_FRAME_{n.upper()} = {i},\n" for i, n in enumerate(names)]
    h.append(f"  MASCOT_FRAME_COUNT = {len(names)}\n}};\n\n")
    h.append("/** @brief Animações disponíveis (uma por estado do assistente). */\n")
    h.append("enum mascot_anim_id : uint8_t {\n")
    h += [f"  MASCOT_ANIM_{s} = {i},\n" for i, s in enumerate(ANIMS)]
    h.append(f"  MASCOT_ANIM_COUNT = {len(ANIMS)}\n}};\n\n")
    h.append("extern const uint16_t mascot_palette[MASCOT_PALETTE_SIZE];  ///< RGB565\n")
    h.append("extern const uint8_t mascot_frames[MASCOT_FRAME_COUNT][MASCOT_FRAME_BYTES];"
             "  ///< 4 bpp, nibble alto = pixel da esquerda\n")
    h.append("extern const mascot_anim_t mascot_anims[MASCOT_ANIM_COUNT];\n")
    (FW_SRC / "mascot_data.h").write_text("".join(h))

    pal = [(0, 0, 0)] * 16
    for idx, rgb in PALETTE.values():
        pal[idx] = rgb
    c = [banner, '#include "mascot_data.h"\n\n',
         "const uint16_t mascot_palette[MASCOT_PALETTE_SIZE] = {\n  "
         + ", ".join(f"0x{rgb565(p):04X}" for p in pal) + "\n};\n\n",
         "const uint8_t mascot_frames[MASCOT_FRAME_COUNT][MASCOT_FRAME_BYTES] PROGMEM = {\n"]
    for n in names:
        data = pack_4bpp(grids[n])
        c.append(f"  {{  // {n}\n")
        for i in range(0, len(data), 16):
            c.append("    " + ", ".join(f"0x{b:02X}" for b in data[i:i + 16]) + ",\n")
        c.append("  },\n")
    c.append("};\n\n")
    for s, anim in ANIMS.items():
        c.append(f"static const mascot_step_t anim_{s.lower()}[] = {{\n")
        c += [f"  {{MASCOT_FRAME_{n.upper()}, {ms}}},\n" for n, ms in anim["steps"]]
        c.append("};\n")
    c.append("\nconst mascot_anim_t mascot_anims[MASCOT_ANIM_COUNT] = {\n")
    for s, anim in ANIMS.items():
        core, glow = anim["gem"]
        c.append(f"  {{anim_{s.lower()}, {len(anim['steps'])}, "
                 f"0x{rgb565(core):04X}, 0x{rgb565(glow):04X}}},\n")
    c.append("};\n")
    (FW_SRC / "mascot_data.cpp").write_text("".join(c))


def main():
    """!
    @brief Compõe todos os quadros e grava firmware + preview.

    @return None.
    """
    grids = {name: compose(**params) for name, params in FRAMES.items()}
    build_preview(grids)
    write_firmware(grids)
    print(f"{len(grids)} quadros, {len(grids) * W * H // 2} bytes de sprite")


if __name__ == "__main__":
    main()
