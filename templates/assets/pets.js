// ILANG
// TYPE:asset ROLE:critter
// ::RULE{a pixel critter drawn from code only: no images, no fonts, no network, no storage}
// ::RULE{it must never cover prices or links: it lives in one fixed corner and can be hidden}
// ::RULE{honour prefers-reduced-motion: no autonomous wandering for those users}
// ::BOUNDARY{never:collect or transmit anything|scope:file}
// ::BOUNDARY{never:block a click that was meant for a link|scope:file}
(function () {
  'use strict';

  var host = document.querySelector('.critter');
  if (!host || !host.appendChild) return;

  var reduceMotion = false;
  try { reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}

  var W = 26, H = 26, S = 4;
  var canvas = document.createElement('canvas');
  canvas.width = W * S;
  canvas.height = H * S;
  canvas.setAttribute('aria-hidden', 'true');
  canvas.setAttribute('title', 'pet the cat');
  canvas.style.touchAction = 'manipulation';
  host.appendChild(canvas);

  var hider = document.createElement('button');
  hider.className = 'hider';
  hider.type = 'button';
  hider.setAttribute('aria-label', 'hide the pixel cat');
  hider.textContent = '\u00d7';
  hider.addEventListener('click', function (event) {
    event.stopPropagation();
    host.remove();
  });
  host.appendChild(hider);

  var g = canvas.getContext('2d');
  g.imageSmoothingEnabled = false;

  var C = {
    outline: '#141c28',
    fur: '#eef2f8',
    shade: '#c6d0e0',
    ink: '#1b2434',
    glint: '#8fd6ff',
    accent: '#f6821f',
    heart: '#ff5d7a',
    star: '#ffd479',
    zzz: '#93a3b8'
  };

  // rounding helper: every shape is a list of [x, y, w, h, colour] pixel rects
  function rect(list, x, y, w, h, colour, flip) {
    if (flip) x = W - x - w;
    list.push([x, y, w, h, colour]);
  }

  function pushSprite(list, art, ox, oy, colour, flip) {
    for (var y = 0; y < art.length; y++) {
      var row = art[y];
      for (var x = 0; x < row.length; x++) {
        if (row[x] === '#') rect(list, ox + x, oy + y, 1, 1, colour, flip);
      }
    }
  }

  var HEART = ['.##.##.', '#######', '#######', '.#####.', '..###..', '...#...'];
  var STAR = ['...#...', '...#...', '#######', '...#...', '...#...', '..###..'];
  var ZED = ['#####', '...#.', '..#..', '.#...', '#####'];

  var HEART_W = HEART[0].length, HEART_H = HEART.length;
  var STAR_W = STAR[0].length, STAR_H = STAR.length;
  var ZED_W = ZED[0].length, ZED_H = ZED.length;

  // ------------------------------------------------------------------ state

  var state = {
    mode: 'idle',        // idle | walk | sleep | jump | excited
    facing: 1,           // 1 = right, -1 = left
    step: 0,             // walk cycle
    offsetX: 0,
    jump: 0,
    blinkUntil: 0,
    nextBlink: 0,
    nextWander: 0,
    exciteUntil: 0,
    lastTouch: 0,
    bob: 0,
    particles: [],
    hidden: false
  };

  function now() { return performance.now(); }

  function touch() {
    state.lastTouch = now();
    if (state.mode === 'sleep') state.mode = 'idle';
  }

  function excite() {
    touch();
    state.exciteUntil = now() + 1200;
    spawn('star', 3);
  }

  function spawn(kind, count) {
    for (var i = 0; i < count; i++) {
      state.particles.push({
        kind: kind,
        x: 9 + Math.random() * 8,
        y: 8 + Math.random() * 3,
        vy: 0.16 + Math.random() * 0.12,
        vx: (Math.random() - 0.5) * 0.12,
        life: 1,
        born: now(),
        ttl: 1500 + Math.random() * 500
      });
    }
  }

  canvas.addEventListener('pointerdown', function () {
    touch();
    state.mode = 'jump';
    state.jump = 1;
    state.exciteUntil = now() + 1500;
    spawn('heart', 4);
  });

  canvas.addEventListener('pointerenter', function () {
    touch();
    state.exciteUntil = Math.max(state.exciteUntil, now() + 600);
  });

  // look towards the pointer when it is near the corner
  var lookX = 0, lookY = 0;
  document.addEventListener('pointermove', function (event) {
    var rectBox = host.getBoundingClientRect();
    var dx = event.clientX - (rectBox.left + rectBox.width / 2);
    var dy = event.clientY - (rectBox.top + rectBox.height / 2);
    var dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 260) {
      lookX = Math.max(-1, Math.min(1, dx / 120));
      lookY = Math.max(-1, Math.min(1, dy / 120));
    } else {
      lookX = 0; lookY = 0;
    }
  }, { passive: true });

  // get excited when the visitor points at a price or a call to action
  document.addEventListener('pointerover', function (event) {
    var target = event.target;
    if (target && target.closest && target.closest('a.btn, .cta, .price')) excite();
  }, { passive: true });

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) { state.lastTouch = now(); }
  });

  // ----------------------------------------------------------------- render

  function drawCat(list, t) {
    var flip = state.facing < 0;
    var bob = state.bob;
    var walking = state.mode === 'walk';
    var legPhase = walking ? Math.floor(state.step) % 2 : 0;

    // tail (behind the body)
    var sway = Math.round(Math.sin(t / 420) * 1.6) + (state.exciteUntil > now() ? Math.round(Math.sin(t / 110)) : 0);
    rect(list, 19, 15 + bob + sway, 3, 1, C.outline, flip);
    rect(list, 20, 13 + bob + sway, 3, 2, C.outline, flip);
    rect(list, 20, 12 + bob + sway, 2, 2, C.fur, flip);

    // ears
    rect(list, 7, 5 + bob, 3, 3, C.outline, flip);
    rect(list, 8, 6 + bob, 1, 2, C.accent, flip);
    rect(list, 15, 5 + bob, 3, 3, C.outline, flip);
    rect(list, 16, 6 + bob, 1, 2, C.accent, flip);

    // head
    rect(list, 8, 7 + bob, 9, 1, C.outline, flip);
    rect(list, 6, 8 + bob, 13, 4, C.outline, flip);
    rect(list, 7, 8 + bob, 11, 3, C.fur, flip);
    rect(list, 7, 11 + bob, 11, 1, C.shade, flip);

    // body
    rect(list, 6, 12 + bob, 13, 1, C.outline, flip);
    rect(list, 5, 13 + bob, 15, 5, C.outline, flip);
    rect(list, 6, 13 + bob, 13, 4, C.fur, flip);
    rect(list, 6, 17 + bob, 13, 1, C.shade, flip);

    // front legs
    var lift = walking ? (legPhase ? 1 : 0) : 0;
    rect(list, 7, 18 + bob - lift, 3, 3, C.outline, flip);
    rect(list, 15, 18 + bob - (walking && !legPhase ? 1 : 0), 3, 3, C.outline, flip);
    rect(list, 8, 18 + bob - lift, 2, 2, C.fur, flip);
    rect(list, 16, 18 + bob - (walking && !legPhase ? 1 : 0), 2, 2, C.fur, flip);

    // collar + bell (site accent colour)
    rect(list, 7, 12 + bob, 11, 1, C.accent, flip);
    rect(list, 12, 13 + bob, 1, 1, C.star, flip);

    // face: eyes / nose / whiskers
    var sleeping = state.mode === 'sleep';
    var blinking = !sleeping && now() < state.blinkUntil;
    var happy = state.exciteUntil > now() || state.mode === 'jump';
    var ex = Math.round(lookX);
    var ey = Math.round(lookY) > 0 ? 1 : 0;

    if (sleeping || blinking) {
      rect(list, 9, 9 + bob, 2, 1, C.ink, flip);
      rect(list, 14, 9 + bob, 2, 1, C.ink, flip);
    } else if (happy) {
      rect(list, 9, 9 + bob, 1, 1, C.ink, flip);
      rect(list, 10, 8 + bob, 1, 1, C.ink, flip);
      rect(list, 15, 8 + bob, 1, 1, C.ink, flip);
      rect(list, 16, 9 + bob, 1, 1, C.ink, flip);
    } else {
      rect(list, 9 + ex, 9 + bob + ey, 2, 2, C.ink, flip);
      rect(list, 14 + ex, 9 + bob + ey, 2, 2, C.ink, flip);
      rect(list, 9 + ex, 9 + bob + ey, 1, 1, C.glint, flip);
      rect(list, 14 + ex, 9 + bob + ey, 1, 1, C.glint, flip);
    }

    // nose + whiskers
    rect(list, 11, 11 + bob, 3, 1, C.heart, flip);
    rect(list, 4, 10 + bob, 3, 1, C.shade, flip);
    rect(list, 18, 10 + bob, 3, 1, C.shade, flip);
  }

  function render(t) {
    var list = [];
    var lift = state.mode === 'jump' ? Math.round(Math.sin(Math.min(1, state.jump) * Math.PI) * 4) : 0;

    g.clearRect(0, 0, canvas.width, canvas.height);
    g.save();
    g.scale(S, S);
    g.translate(state.offsetX, -lift);
    drawCat(list, t);
    g.restore();

    for (var i = 0; i < list.length; i++) {
      var r = list[i];
      g.fillStyle = r[4];
      g.fillRect(r[0] * S, r[1] * S, r[2] * S, r[3] * S);
    }

    // particles: hearts on a pet, stars when excited, Zzz while asleep
    var alive = [];
    for (var p = 0; p < state.particles.length; p++) {
      var q = state.particles[p];
      var age = now() - q.born;
      if (age > q.ttl) continue;
      var y = q.y - q.vy * age / 16;
      var x = q.x + q.vx * age / 16;
      var art = q.kind === 'heart' ? HEART : STAR;
      var colour = q.kind === 'heart' ? C.heart : C.star;
      var fade = 1 - age / q.ttl;
      g.globalAlpha = Math.max(0, Math.min(1, fade));
      for (var ay = 0; ay < art.length; ay++) {
        for (var ax = 0; ax < art[ay].length; ax++) {
          if (art[ay][ax] === '#') g.fillRect(Math.round(x + ax) * S, Math.round(y + ay) * S, S, S);
        }
      }
      g.globalAlpha = 1;
      alive.push(q);
    }
    state.particles = alive;

    if (state.mode === 'sleep') {
      var zAge = (t % 1800) / 1800;
      g.globalAlpha = Math.max(0, 1 - zAge);
      for (var zy = 0; zy < ZED_H; zy++) {
        for (var zx = 0; zx < ZED_W; zx++) {
          if (ZED[zy][zx] === '#') {
            g.fillRect((17 + zx) * S, Math.round(6 + zy - zAge * 4) * S, S, S);
          }
        }
      }
      g.globalAlpha = 1;
    }
  }

  // ------------------------------------------------------------------- loop

  var last = now();
  var tick = 1000 / 14; // 14 fps: chunky, cheap, and easy on the battery

  function frame() {
    if (document.hidden) { requestAnimationFrame(frame); return; }
    var t = now();
    if (t - last < tick) { requestAnimationFrame(frame); return; }
    var dt = t - last;
    last = t;

    state.bob = Math.sin(t / 520) > 0.7 ? 1 : 0;

    if (state.mode === 'jump') {
      state.jump -= dt / 420;
      if (state.jump <= 0) { state.jump = 0; state.mode = 'idle'; }
    }

    if (state.mode === 'idle' || state.mode === 'walk') {
      if (t > state.nextBlink) {
        state.blinkUntil = t + 130;
        state.nextBlink = t + 2600 + Math.random() * 3600;
      }
      if (!reduceMotion && t - state.lastTouch > 22000) {
        state.mode = 'sleep';
      } else if (!reduceMotion && state.mode === 'idle' && t > state.nextWander) {
        state.mode = 'walk';
        state.step = 0;
        state.facing = Math.random() < 0.5 ? 1 : -1;
      }
    }

    if (state.mode === 'walk') {
      state.step += dt / 260;
      state.offsetX += state.facing * dt / 90;
      if (state.offsetX > 3) { state.offsetX = 3; state.facing = -1; }
      if (state.offsetX < -3) { state.offsetX = -3; state.facing = 1; }
      if (state.step > 4) {
        state.mode = 'idle';
        state.offsetX = 0;
        state.nextWander = t + 4000 + Math.random() * 7000;
      }
    }

    render(t);
    requestAnimationFrame(frame);
  }

  state.lastTouch = now();
  state.nextBlink = now() + 1800;
  state.nextWander = now() + 3500;
  requestAnimationFrame(frame);
})();
