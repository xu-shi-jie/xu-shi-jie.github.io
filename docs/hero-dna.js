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
  // A codon for each letter the site links can spell, so the strand above a link really
  // encodes it: O is pyrrolysine (read through the amber stop TAG), B is Asx (D or N),
  // spelled with the IUPAC code R = A/G as RAT (GAT = D, AAT = N).
  const CODON = {
    A: 'GCC', B: 'RAT', C: 'TGC', D: 'GAT', E: 'GAA', F: 'TTC', G: 'GGC', H: 'CAT',
    I: 'ATC', K: 'AAG', L: 'CTG', M: 'ATG', N: 'AAC', O: 'TAG', P: 'CCC', Q: 'CAG',
    R: 'CGC', S: 'AGC', T: 'ACC', U: 'TGA', V: 'GTG', W: 'TGG', Y: 'TAC',
  };
  const STOP = 'TAA';      // between two link words, drawn as a stop residue '·'
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
  // IUPAC R (A or G) takes the colour halfway between A and G
  const baseColor = b => C[b] || (b === 'R' ? mix(C.A, C.G, 0.5) : C.ink);
  const mix = (a, b, t) => a.map((x, i) => Math.round(x + (b[i] - x) * t));
  const css = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  function mount(el) {
    const cv = document.createElement('canvas');
    cv.setAttribute('aria-hidden', 'true');
    el.appendChild(cv);
    const ctx = cv.getContext('2d');
    let W = 0, H = 0, dpr = 1;

    // Site links set into the translation row: each letter takes one residue slot. The
    // letters are painted on the canvas like the residues; the <a> elements stay in the
    // DOM, transparent, as the click / focus / crawl targets laid over them.
    const nav = el.querySelector('.hero-nav');
    const links = nav ? [...nav.querySelectorAll('a')] : [];
    const toggle = nav && nav.querySelector('.theme-toggle');
    let hot = null;  // link under the pointer or keyboard focus
    for (const a of links) {
      const on = () => { hot = a; draw(); }, off = () => { if (hot === a) { hot = null; draw(); } };
      a.addEventListener('pointerenter', on); a.addEventListener('pointerleave', off);
      a.addEventListener('focus', on); a.addEventListener('blur', off);
    }
    if (nav) nav.classList.add('laid');

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

      // px per base pair, narrowed on very small screens until the links fit the column
      const colL = W >= 832 ? (W - 800) / 2 : 16, colR = W - colL;
      // the toggle needs its own slot plus a gap, or on a phone it has no room left in the row
      const nSlots = links.reduce((n, a) => n + a.textContent.trim().length + 1, 0) + (toggle ? 2 : 0);
      const cw = Math.min(W < 600 ? 12 : 15, (colR - colL) / (3 * Math.max(nSlots, 1)));
      const cx = W / 2, cy = H * 0.38, R = H * 0.17;
      // bp index under the centre line; on wide screens shift it right so the gene's ATG
      // sits at or beyond the left edge instead of the gap and the gene's wrapped-around tail
      const off = Math.max(57, Math.ceil(cx / cw));
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

      // residue slots taken by the links: start at the content column's left edge, one
      // blank slot between words; the theme toggle takes the last slot before its right edge
      const yNt = H * 0.74, yAa = H * 0.92;
      const taken = new Set(), words = [];
      // rewritten bases (bp index -> base) and the ones that belong to a link's codons
      const nt = new Map(), linkNt = new Set();
      const setCodon = (k, c) => { nt.set(k - 1, c[0]).set(k, c[1]).set(k + 1, c[2]); };
      // the residue slot nearest to where a letter at the column's left edge would sit
      let k = Math.round((off + (colL + 6 - cx) / cw - 1) / 3) * 3 + 1;
      while (xOf(k) < 8) k += 3;
      links.forEach((a, n) => {
        if (n) { setCodon(k, STOP); k += 3; }  // a stop codon between words
        const t = a.textContent.trim().toUpperCase(), ks = [];
        for (let j = 0; j < t.length; j++, k += 3) {
          ks.push(k); taken.add(k);
          if (CODON[t[j]]) { setCodon(k, CODON[t[j]]); linkNt.add(k - 1).add(k).add(k + 1); }
        }
        words.push({ a, t, ks });
      });
      // a stop codon after the last word too, so the next residue never reads as part of it
      if (links.length) setCodon(k, STOP);
      k += 3;
      let kT = Math.floor(off + (colR - 8 - cx) / cw);
      while (mod(kT, 3) !== 1) kT--;
      const tFits = kT >= k;
      // the toggle's codon is a point mutation away from dark: TGG (Trp, the residue that
      // absorbs and fluoresces) in the light theme, TGA (stop: the light goes out) in the dark
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (tFits) {
        taken.add(kT);
        setCodon(kT, dark ? 'TGA' : 'TGG');
        linkNt.add(kT - 1).add(kT).add(kT + 1);
      }

      // coding strand (the only colour in the hero) and its translation
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      for (let k = kMin; k <= kMax; k++) {
        const b = nt.get(k) || baseAt(k);
        if (!b) continue;
        const x = xOf(k), e = em(x);
        if (!linkNt.has(k)) {
          ctx.font = `300 10.5px ${MONO}`;
          ctx.fillStyle = css(baseColor(b), 0.25 + 0.6 * e);
          ctx.fillText(b, x, yNt);
        }
        const i = mod(k, PERIOD);
        if (i % 3 !== 1 || taken.has(k)) continue;
        const aa = nt.has(k) ? '*' : aaOf((i - 1) / 3);
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

      // the links, painted last so the edge fade never dims them
      ctx.font = `300 17px ${SERIF}`;
      for (const { a, t, ks } of words) {
        const cur = a.getAttribute('aria-current'), on = hot === a;
        const x0 = xOf(ks[0]), x1 = xOf(ks[ks.length - 1]);
        // the link's codons, also painted after the fade
        ctx.font = `300 10.5px ${MONO}`;
        for (const k of ks) for (const q of [k - 1, k, k + 1]) {
          const b = nt.get(q);
          if (!b || !linkNt.has(q)) continue;
          ctx.fillStyle = css(baseColor(b), cur || on ? 0.95 : 0.7);
          ctx.fillText(b, xOf(q), yNt);
        }
        ctx.font = `300 17px ${SERIF}`;
        ctx.fillStyle = css(C.ink, cur || on ? 1 : 0.62);
        for (let j = 0; j < t.length; j++) ctx.fillText(t[j], xOf(ks[j]), yAa);
        // underline: solid under the current page, faint under the others until hovered
        ctx.fillStyle = css(C.ink, cur ? 0.9 : on ? 0.7 : 0.22);
        ctx.fillRect(x0 - 6, yAa + 4, x1 - x0 + 12, cur ? 1.5 : 1);
        Object.assign(a.style, {
          left: `${x0 - 1.5 * cw}px`, width: `${x1 - x0 + 3 * cw}px`,
          top: `${yAa - 20}px`, height: `${H - yAa + 20}px`,
        });
      }
      if (tFits) {
        ctx.font = `300 10.5px ${MONO}`;
        for (const q of [kT - 1, kT, kT + 1]) {
          ctx.fillStyle = css(baseColor(nt.get(q)), 0.9);
          ctx.fillText(nt.get(q), xOf(q), yNt);
        }
      }
      if (toggle) {
        const tx = tFits ? xOf(kT) : colR - 10, ty = tFits ? yAa - 6 : 16;
        Object.assign(toggle.style, { left: `${tx}px`, top: `${ty}px` });
      }
    }

    readColors(el);
    new MutationObserver(() => { readColors(el); draw(); })
      .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    new ResizeObserver(resize).observe(el);
    // The subset fonts arrive through a non-blocking stylesheet (#hero-fonts); canvas text
    // does not request them by itself, so load them once that sheet is in, then redraw.
    const loadFonts = () => document.fonts && Promise.all([
      document.fonts.load(`300 10.5px "Roboto Mono"`, 'ACGRT'),
      document.fonts.load(`300 17px "Roboto Serif"`, CODE),
    ]).then(draw, () => {});
    const sheet = document.getElementById('hero-fonts');
    if (sheet && sheet.media === 'all') loadFonts();
    else if (sheet) sheet.addEventListener('load', loadFonts);
    resize();
  }

  // Pages load this file synchronously in <head> and call heroMount() from an inline
  // <script> right after the .hero element, so the hero is laid out while the parser is
  // still there and no browser can paint it first. (A deferred script with
  // blocking="render" did that only in Chromium: Firefox painted the bare gradient and
  // the unlaid links on every page change, a visible flash.)
  window.heroMount = () => document.querySelectorAll('.hero:not([data-mounted])').forEach(el => {
    el.dataset.mounted = '';
    mount(el);
  });
})();
