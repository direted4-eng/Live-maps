# Art Prompts — Pixel Art Tracker

Промпты для генерации арта в нейросетях (Claude image tool / Midjourney / DALL·E 3 / Imagen / Nano Banana / Stable Diffusion).

Все промпты на английском — модели лучше понимают английский для визуальных задач. Русские заметки оставлены для тебя.

---

## Базовый стиль

Этот блок копируется в начало каждого промпта, чтобы держать все картинки в одной стилистике.

```
pixel art, 16-bit JRPG / Stardew Valley style, cozy aesthetic,
soft warm lighting, limited cohesive palette,
crisp 1px outlines, no anti-aliasing, no gradients (use dithering for shading only),
no text, no letters, no watermarks,
centered subject, clean composition.
```

### Палитра (придерживайся её во всех артах)

| Hex | Назначение |
|---|---|
| `#A2CFFD` | небо, голубые акценты |
| `#4F9B43` | зелень, прогресс-бары |
| `#AF8F6B` | дерево, мебель |
| `#EFE0D0` | бумага, фон карточек |
| `#9B4F43` | терракот, акценты |
| `#3D2E1F` | тёмные контуры, тени |

Доп. палитра для **ночной/cyberpunk** версии:

| Hex | Назначение |
|---|---|
| `#1F2A44` | ночное небо |
| `#FF6B9D` | неон розовый |
| `#44E0FF` | неон голубой |
| `#FFB347` | тёплый свет лампы |

---

## 1. Главная сцена — комната

Три фона: **день**, **закат**, **ночь**. Все три имеют одинаковую композицию интерьера, отличается только вид из окна и общее освещение. Это позволит подменять только фоновый слой по времени суток.

**Композиция (общая для всех трёх):**
- Вид прямо, slightly front-on perspective
- Большое окно по центру (≈55% ширины)
- Деревянный письменный стол в нижней половине, поверхность ПУСТАЯ (предметы будут наложены спрайтами)
- Тонкая книжная полка справа с книгами и небольшими анатомическими моделями (мозг, череп, позвоночник)
- Маленький бонсай в тёмно-синем горшке на деревянном табурете слева
- Деревянный пол с ковриком по центру
- Aspect ratio: **16:10**, target 1280×800px

### 1.1 День

```
pixel art, 16-bit JRPG / Stardew Valley style, cozy aesthetic,
soft warm lighting, limited cohesive palette
(#A2CFFD sky, #4F9B43 green, #AF8F6B wood, #EFE0D0 cream,
 #9B4F43 terracotta, #3D2E1F dark brown outlines),
crisp 1px outlines, no anti-aliasing, no gradients (dithering only),
no text, no letters, no watermarks.

Wide cozy study room interior, viewed straight-on.
Large central window showing a bright sunny green meadow with
rolling hills, scattered round-canopy trees, soft cumulus clouds
in pale blue sky, distant misty mountains.
Wooden desk in foreground, EMPTY desktop surface
(no objects on it — they will be overlaid as sprites later).
Slim bookshelf on the right with books and small anatomical
models (brain, skull, spine). Small bonsai tree in a dark blue
ceramic pot on a wooden stool on the left.
Wooden floor with a small rug centered under the desk.
Aspect ratio 16:10, 1280x800 pixels, true pixel art.
```

### 1.2 Закат

```
[same base style as Day]

Same cozy study room, same composition, EVENING GOLDEN HOUR
through the window: warm orange and peach sky with soft pink
clouds, distant mountains in cool purple silhouette, trees as
warm-rim-lit silhouettes. Interior lit by a warm desk lamp glow,
longer shadows on the floor, overall warmer color cast.
EMPTY desktop surface. 1280x800 pixels, pixel art.
```

### 1.3 Ночь (cyberpunk-вариант, как 3-й референс)

```
pixel art, 16-bit JRPG style, cozy lo-fi aesthetic,
night palette (#1F2A44 night sky, #FF6B9D neon pink,
 #44E0FF neon cyan, #FFB347 warm lamp light,
 #AF8F6B wood, #3D2E1F dark outlines),
crisp 1px outlines, dithering only, no text, no letters.

Same cozy study room, same composition, NIGHT.
Large window shows a dense neon cyberpunk cityscape:
distant skyscrapers with glowing red and cyan signs, warm yellow
window lights at varied heights, vague kanji-shaped neon glyphs
(NO readable text — abstract shapes only), soft cloud streaks.
Interior lit only by a tall warm-cream floor lamp on the right;
desk surface gently illuminated, deep blue shadows elsewhere.
EMPTY desktop surface. Mood: peaceful, lo-fi.
1280x800 pixels, pixel art.
```

---

## 2. Спрайты предметов (UI-навигация)

Все предметы — отдельные PNG **128×128** на прозрачном фоне. Для каждого нужны **два кадра**:

1. `idle` — обычное состояние
2. `hover` — то же + мягкое свечение по контуру (~4px outer glow)

**Шаблон промпта:**

```
pixel art, 16-bit JRPG / Stardew Valley style,
palette (#A2CFFD, #4F9B43, #AF8F6B, #EFE0D0, #9B4F43, #3D2E1F),
crisp 1px outlines, no anti-aliasing, dithering only,
no text, no letters, no watermarks.

Single object centered on TRANSPARENT background, 128x128 pixels,
clean readable silhouette, suitable as a clickable UI icon.

Object: <OBJECT_DESCRIPTION>

Output TWO versions side by side:
(1) normal idle state,
(2) same object with subtle 4px soft outer glow halo (warm cream
    light #EFE0D0 at 40% opacity) for hover state.
```

Подставляй `<OBJECT_DESCRIPTION>` из таблицы ниже.

### 2.1 Предметы навигации

| Раздел | OBJECT_DESCRIPTION | Файл |
|---|---|---|
| Учёба | `human brain anatomical model, pinkish-red with darker grooves, on a small wooden cylindrical stand with a tiny brass plaque` | `brain.png` |
| Расписание | `thick leather-bound planner book, dark brown leather cover with a small embossed cross, red bookmark ribbon, sitting beside a stack of two smaller books` | `planner.png` |
| Финансы | `pixel-art piggy bank, terracotta-red ceramic, classic chubby shape, with a small coin slot on the back and a single gold coin balancing on top, tiny gold sparkles around` | `piggy.png` |
| Привычки / фокус | `Hario V60 dripper red plastic cone on a clear glass server with dark coffee inside, a small white ceramic coffee cup beside it on a saucer, a thin wisp of steam` | `v60.png` |
| Советы Hermes | `rolled parchment scroll tied with a red ribbon, a round wax seal stamped with letter H, scroll glowing faintly with a soft warm aura` | `scroll.png` |

### 2.2 Декор (не кликабельный, для атмосферы)

| Предмет | OBJECT_DESCRIPTION | Файл |
|---|---|---|
| Бонсай | `small bonsai tree with a thick twisted trunk and lush round green canopy, in a dark blue rectangular ceramic pot with a shallow tray` | `bonsai.png` |
| Позвоночник | `anatomical spine model, ivory-white vertebrae stacked on a thin chrome metal stand with a heavy black base` | `spine.png` |
| Череп | `small anatomical human skull model, off-white ivory color, sitting on a thin wooden stand, slight side-angle view` | `skull.png` |
| Лампа (ночь) | `tall pixel floor lamp, slim wooden pole, cream pleated lampshade, glowing warm yellow light from inside` | `lamp.png` |

---

## 3. UI-элементы (опционально — можно сделать CSS-ом)

Если хочешь готовые PNG-рамки вместо CSS-бордеров.

### 3.1 Рамка карточки (9-slice)

```
pixel art, palette (#EFE0D0 cream, #AF8F6B wood, #3D2E1F dark, #FFFFFF highlight),
no anti-aliasing.

Pixel-art UI frame corner tile, 32x32 pixels, transparent background.
Cream interior (#EFE0D0), 2px dark brown outline (#3D2E1F),
1px white inner highlight on top and left edges,
1px warm-brown shadow (#AF8F6B) on bottom and right edges.
Creates a soft beveled "window" appearance.
Must tile cleanly as a 9-slice (output the top-left corner;
edges and center can be derived).
```

### 3.2 Кнопка-чип (3 состояния)

```
pixel art, same palette as frame.

Pixel-art button "chip", rounded square 96x96 pixels each.
Three vertically stacked states on transparent background:
(1) IDLE: flat cream face #EFE0D0, 2px dark brown bevel,
    top-left highlight, bottom-right shadow.
(2) HOVER: same but with a 1px brighter highlight and a faint
    warm cream glow around the chip.
(3) PRESSED: same chip but visually offset 2px down-right,
    shadow on top-left now (depressed look).
No text on the buttons.
```

### 3.3 Прогресс-бар

```
pixel art, palette (#EFE0D0, #AF8F6B, #3D2E1F, #4F9B43).

Horizontal pixel-art progress bar, 256x32 pixels, transparent
background. Cream outer frame with dark brown 2px bevel.
Inner fill is chunky green (#4F9B43) with dithered shading and
a 1px brighter top highlight line, subtle scanline texture.
Output THREE frames stacked vertically:
- 25% filled
- 60% filled
- 100% filled
```

### 3.4 Иконки-статусы для карточек советов

```
pixel art, 32x32 pixels each, transparent background, no text.

Output a 5-icon set, horizontally aligned:
(1) glowing yellow exclamation triangle — warning,
(2) green leaf with a small white sparkle — tip,
(3) red flame — urgent,
(4) blue lightbulb glowing — idea,
(5) gray clock face with hands at 10:10 — overdue/time.
```

---

## 4. Куда складывать готовые файлы

После генерации сложи PNG в репозиторий по такой структуре — код будет искать их по этим путям.

```
apps/web/public/sprites/
├── rooms/
│   ├── day.png         (1280x800)
│   ├── sunset.png      (1280x800)
│   └── night.png       (1280x800)
├── items/
│   ├── brain.png       (128x128, idle+hover)
│   ├── planner.png
│   ├── piggy.png
│   ├── v60.png
│   ├── scroll.png
│   ├── bonsai.png
│   ├── spine.png
│   ├── skull.png
│   └── lamp.png
├── ui/
│   ├── frame-corner.png
│   ├── button-states.png
│   └── progress.png
└── icons/
    ├── warn.png
    ├── tip.png
    ├── urgent.png
    ├── idea.png
    └── clock.png
```

---

## 5. Советы по генерации

1. **Сначала прогони сцены комнаты** — на них опираешься цветом и масштабом, потом подгоняешь предметы.
2. **Генерируй пачкой и выбирай** — пиксель-арт у нейросетей нестабильный, лучше получить 4–8 вариантов и взять лучший.
3. **Если модель добавляет текст/буквы** — добавь в негатив: `no text, no letters, no captions, no signs, no words, no logos`.
4. **Если выходит мыльно (не настоящий пиксель)** — добавь: `true pixel art, sharp pixel grid visible, blocky pixels, no smoothing, no blur, retro game sprite`.
5. **Размер**: проси модель целиться в большое разрешение (1024+), потом downscale до точного целевого через **nearest-neighbor** в Photoshop/GIMP/Aseprite, иначе пиксели «поплывут».
6. **Прозрачность для предметов** — большинство моделей не выдаёт чистую альфу, проще генерить на ровном лаймовом фоне (`#00FF00`) и потом вычитать в редакторе.
7. **Консистентность**: при генерации второго и третьего фона комнаты передавай первый как референс (image-to-image), иначе мебель «поплывёт».

---

## 6. Что под рукой полезно

- **Aseprite** (~$20) — родной редактор для пиксель-арта, идеален для подчистки и экспорта спрайт-листов.
- **Piskel** (бесплатно, веб) — лёгкая альтернатива.
- **TinyPNG** — пожать готовые PNG перед коммитом в репо.
- **ImageMagick** — `convert input.png -resize 128x128 -filter point output.png` для корректного downscale без размытия.
