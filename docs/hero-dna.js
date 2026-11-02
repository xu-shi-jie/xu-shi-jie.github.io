// Site hero: a still B-DNA double helix carrying a real gene, with the coding strand
// and its codon-by-codon translation underneath. Drawn once into a canvas inside every
// .hero element; colours come from the --dna-* tokens so it follows the theme. Without
// JS the .hero keeps its CSS gradient.
//
// Sequence: chicken lysozyme C, LYZ coding sequence (NCBI NM_205281.2, CDS 32..475, incl. stop).
(function () {
  const CDS = 'ATGAGGTCTTTGCTAATCTTGGTGCTTTGCTTCCTGCCCCTGGCTGCTCTGGGGAAAGTCTTTGGACGATGTGAGCTGGCAGCGGCTATGAAGCGTCACGGACTTGATAACTATCGGGGATACAGCCTGGGAAACTGGGTGTGTGCCGCAAAATTCGAGAGTAACTTCAACACCCAGGCTACAAACCGTAACACCGATGGGAGTACCGACTACGGAATCCTACAGATCAACAGCCGCTGGTGGTGCAACGATGGCAGGACCCCAGGCTCCAGGAACCTGTGCAACATCCCGTGCTCAGCCCTGCTGAGCTCAGACATAACAGCGAGCGTGAACTGCGCGAAGAAGATCGTCAGCGATGGAAACGGCATGAACGCGTGGGTCGCCTGGCGCAACCGCTGCAAGGGCACCGACGTCCAGGCGTGGATCAGAGGCTGCCGGCTGTGA';
  const NB = CDS.length;
  const GAP = 12;          // bare helix between repeats of the gene
  const PERIOD = NB + GAP;
  const BP_TURN = 10.5;    // B-DNA
  const GROOVE = 2.4;      // strand 2 phase offset (rad): minor/major groove
  const IDX = { T: 0, C: 1, A: 2, G: 3 };
  const CODE = 'FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG';
  const SERIF = '"Roboto Serif", Georgia, serif';
  const MONO = '"Roboto Mono", ui-monospace, Menlo, Consolas, monospace';

  const mod = (a, n) => ((a % n) + n) % n;
  const baseAt = k => { const i = mod(k, PERIOD); return i < NB ? CDS[i] : null; };
  const aaOf = c => CODE[16 * IDX[CDS[3 * c]] + 4 * IDX[CDS[3 * c + 1]] + IDX[CDS[3 * c + 2]]];

  let C = {};
  const rgb = v => {
    v = v.trim();
    const n = parseInt(v.length === 4 ? v.slice(1).replace(/./g, c => c + c) : v.slice(1), 16);
    return [n >> 16, (n >> 8) & 255, n & 255];
  };
  function readColors(el) {
    const cs = getComputedStyle(el);
    for (const k of ['bg1', 'bg2', 'strand', 'ink', 'A', 'T', 'G', 'C']) C[k] = rgb(cs.getPropertyValue('--dna-' + k));
    C.rung = parseFloat(cs.getPropertyValue('--dna-rung')) || 0.5;
  }
  const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
  const css = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  function mount(el) {
    const cv = document.createElement('canvas');
    cv.setAttribute('aria-hidden', 'true');
    el.appendChild(cv);
    const ctx = cv.getContext('2d');
    let W = 0, H = 0, dpr = 1;

    function resize() {
      dpr = Math.min(devicePixelRatio || 1, 2);
      W = el.clientWidth; H = el.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr;
      cv.style.width = W + 'px'; cv.style.height = H + 'px';
      draw();
    }

    function draw() {
      if (!W) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, W, H);

      const cw = W < 600 ? 12 : 15;                // px per base pair
      const off = 57;                              // bp index under the centre line
      const cx = W / 2, cy = H * 0.38, R = H * 0.17;
      const xOf = k => cx + (k - off) * cw;
      const at = (u, s) => {
        const th = (2 * Math.PI * u) / BP_TURN + (s ? GROOVE : 0);
        return [cy + R * Math.sin(th), Math.cos(th)];
      };
      const kMin = Math.floor(off - cx / cw) - 1, kMax = Math.ceil(off + (W - cx) / cw) + 1;

      // emphasis: full strength around the centre, tapering toward the sides
      const sig = Math.max(200, W * 0.24);
      const em = x => 0.25 + 0.75 * Math.exp(-(((x - cx) / sig) ** 2));

      // helix in one colour: strand segments and rungs, painted back to front
      const items = [];
      for (let x = 0; x < W; x += 3) {
        const u0 = off + (x - cx) / cw, u1 = off + (x + 3 - cx) / cw;
        for (const s of [0, 1]) {
          const a = at(u0, s), b = at(u1, s);
          items.push({ z: (a[1] + b[1]) / 2, kind: 0, x0: x, y0: a[0], x1: x + 3, y1: b[0], e: em(x + 1.5) });
        }
      }
      for (let k = kMin; k <= kMax; k++) {
        const x = xOf(k), p = at(k, 0), q = at(k, 1), e = em(x);
        if (baseAt(k)) items.push({ z: (p[1] + q[1]) / 2, kind: 1, x, p, q, e });
      }
      items.sort((a, b) => a.z - b.z);
      ctx.lineCap = 'round';
      for (const it of items) {
        const d = (it.z + 1) / 2, f = (0.15 + 0.85 * d) * it.e;
        if (it.kind === 0) {
          ctx.strokeStyle = css(mix(C.bg1, C.strand, f));
          ctx.lineWidth = (0.6 + 1.6 * d) * (0.6 + 0.4 * it.e);
          ctx.beginPath(); ctx.moveTo(it.x0, it.y0); ctx.lineTo(it.x1, it.y1); ctx.stroke();
        } else {
          ctx.strokeStyle = css(mix(C.bg1, C.strand, C.rung * f));
          ctx.lineWidth = (0.6 + 0.5 * d) * (0.7 + 0.3 * it.e);
          ctx.beginPath(); ctx.moveTo(it.x, it.p[0]); ctx.lineTo(it.x, it.q[0]); ctx.stroke();
        }
      }

      // coding strand (the only colour in the hero) and its translation
      const yNt = H * 0.74, yAa = H * 0.92;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      for (let k = kMin; k <= kMax; k++) {
        const b = baseAt(k);
        if (!b) continue;
        const x = xOf(k), e = em(x);
        ctx.font = `300 10.5px ${MONO}`;
        ctx.fillStyle = css(C[b], 0.25 + 0.6 * e);
        ctx.fillText(b, x, yNt);
        const i = mod(k, PERIOD);
        if (i % 3 !== 1) continue;
        const aa = aaOf((i - 1) / 3);
        ctx.font = `300 17px ${SERIF}`;
        ctx.fillStyle = css(C.ink, 0.2 + 0.6 * e);
        ctx.fillText(aa === '*' ? '·' : aa, x, yAa);
      }

      // soft edges; the .hero's CSS gradient shows through
      ctx.globalCompositeOperation = 'destination-in';
      const e = ctx.createLinearGradient(0, 0, W, 0), fade = Math.min(0.18, 140 / W);
      e.addColorStop(0, 'rgba(0,0,0,0)'); e.addColorStop(fade, 'rgba(0,0,0,1)');
      e.addColorStop(1 - fade, 'rgba(0,0,0,1)'); e.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = e; ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'source-over';
    }

    readColors(el);
    new MutationObserver(() => { readColors(el); draw(); })
      .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    new ResizeObserver(resize).observe(el);
    // The subset fonts arrive through a non-blocking stylesheet (#hero-fonts); canvas text
    // does not request them by itself, so load them once that sheet is in, then redraw.
    const loadFonts = () => document.fonts && Promise.all([
      document.fonts.load(`300 10.5px "Roboto Mono"`, 'ACGT'),
      document.fonts.load(`300 17px "Roboto Serif"`, CODE),
    ]).then(draw, () => {});
    const sheet = document.getElementById('hero-fonts');
    if (sheet && sheet.media === 'all') loadFonts();
    else if (sheet) sheet.addEventListener('load', loadFonts);
    resize();
  }

  // Mount after the first paint: reading the tokens and the width forces a style and layout
  // pass, which before first paint costs a full extra recalc on a page with heavy CSS.
  requestAnimationFrame(() => setTimeout(() => document.querySelectorAll('.hero').forEach(mount)));
})();
