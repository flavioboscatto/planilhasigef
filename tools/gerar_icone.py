"""Gera um ícone placeholder pro .exe (assets/icone_app.ico) — marco
geodésico estilizado (triângulo com ponto central, símbolo cartográfico
padrão de vértice geodésico) nas cores do tema do app
(config/theme_tokens.json: verde de "perimetro_titulo"/"area_titulo").

Provisório: troque assets/icone_app.ico por um ícone definitivo quando
tiver um, e aponte sigef_qt.spec pra ele — não precisa rodar este script
de novo pra isso. Fica em assets/ (versionado), não em tools/out/
(gitignorado como saída descartável): o build precisa do arquivo presente
em qualquer clone do repositório.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

VERDE_FUNDO = "#345b3a"
VERDE_CLARO = "#b1c5b5"
BRANCO = "#ffffff"

SAIDA = Path(__file__).resolve().parent.parent / "assets" / "icone_app.ico"
TAMANHOS = [16, 24, 32, 48, 64, 128, 256]


def _desenhar(tamanho: int) -> Image.Image:
    escala = 4
    n = tamanho * escala
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    raio = n * 0.20
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=raio, fill=VERDE_FUNDO)

    cx, cy = n / 2, n / 2
    lado = n * 0.62
    altura = lado * 0.866
    topo = (cx, cy - altura * 0.58)
    esq = (cx - lado / 2, cy + altura * 0.42)
    dir_ = (cx + lado / 2, cy + altura * 0.42)
    d.polygon([topo, esq, dir_], outline=BRANCO, width=max(1, int(n * 0.045)))

    raio_ponto = n * 0.06
    d.ellipse(
        [cx - raio_ponto, cy - raio_ponto * 0.2, cx + raio_ponto, cy + raio_ponto * 1.8],
        fill=VERDE_CLARO,
    )

    return img.resize((tamanho, tamanho), Image.LANCZOS)


def main() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    imagens = [_desenhar(t) for t in TAMANHOS]
    imagens[-1].save(SAIDA, format="ICO", sizes=[(t, t) for t in TAMANHOS])
    print(f"Ícone gerado em {SAIDA}")


if __name__ == "__main__":
    main()
