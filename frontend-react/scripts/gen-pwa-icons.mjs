// Genera los íconos PWA desde public/favicon.svg y verifica que el ícono
// maskable respete la safe zone (radio 40% del canvas) para que el logo no
// quede recortado por las máscaras de Android.
//
//  - pwa-192x192.png          purpose "any"        (logo a sangre completa)
//  - pwa-512x512.png          purpose "any"        (logo a sangre completa)
//  - pwa-512x512-maskable.png purpose "maskable"   (logo al 60%, centrado,
//                                                    dentro del círculo seguro)
//
// El script autoverifica su propio output y termina con exit != 0 si se viola
// la safe zone (nunca comitear un ícono roto sin darse cuenta).
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { mkdir } from 'node:fs/promises'
import sharp from 'sharp'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PUBLIC_DIR = path.resolve(__dirname, '../public')
const SRC = path.join(PUBLIC_DIR, 'favicon.svg')
const CANVAS = 512
const SAFE_RADIUS = 0.4 * CANVAS // safe zone maskable: círculo central de radio 40%
const SAFE_BOX = 0.1 * CANVAS // contenido dentro del cajón central [10%..90%]
const BG = { r: 255, g: 255, b: 255, alpha: 255 }
const SCALE = 0.6 // logo al 60% → esquina a 58.9% × 0.6 = 35.4% < 40%

async function main() {
  const svg = sharp(SRC)
  const any192 = await svg.clone().resize(192, 192).flatten({ background: BG }).png().toBuffer()
  const any512 = await svg.clone().resize(CANVAS, CANVAS).flatten({ background: BG }).png().toBuffer()

  const logoSize = Math.round(CANVAS * SCALE)
  const offset = Math.round((CANVAS - logoSize) / 2)
  const logo = await svg.clone().resize(logoSize, logoSize).png().toBuffer()
  const maskable = await sharp({
    create: { width: CANVAS, height: CANVAS, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } },
  })
    .composite([{ input: logo, left: offset, top: offset }])
    .flatten({ background: BG })
    .png()
    .toBuffer()

  await mkdir(PUBLIC_DIR, { recursive: true })
  await Promise.all([
    sharp(any192).toFile(path.join(PUBLIC_DIR, 'pwa-192x192.png')),
    sharp(any512).toFile(path.join(PUBLIC_DIR, 'pwa-512x512.png')),
    sharp(maskable).toFile(path.join(PUBLIC_DIR, 'pwa-512x512-maskable.png')),
  ])

  verifyMaskable(await sharp(maskable).ensureAlpha().raw().toBuffer({ resolveWithObject: true }))
  console.log('OK pwa-192x192.png, pwa-512x512.png, pwa-512x512-maskable.png (safe zone verificada)')
}

function verifyMaskable({ data, info }) {
  if (info.width !== CANVAS || info.height !== CANVAS) {
    throw new Error(`maskable: dimensión inesperada ${info.width}x${info.height}`)
  }
  const channels = info.channels || 4
  const cx = (CANVAS - 1) / 2
  const cy = (CANVAS - 1) / 2
  let minX = CANVAS, minY = CANVAS, maxX = -1, maxY = -1
  let outsideSafe = 0

  for (let y = 0; y < CANVAS; y++) {
    for (let x = 0; x < CANVAS; x++) {
      const i = (y * CANVAS + x) * channels
      const isBg =
        data[i] === BG.r && data[i + 1] === BG.g && data[i + 2] === BG.b && data[i + 3] === BG.alpha
      if (!isBg) {
        if (x < minX) minX = x
        if (x > maxX) maxX = x
        if (y < minY) minY = y
        if (y > maxY) maxY = y
        const dist = Math.hypot(x - cx, y - cy)
        if (dist > SAFE_RADIUS) outsideSafe++
      }
    }
  }

  const contentHalf = Math.max(maxX - minX + 1, maxY - minY + 1) / 2
  console.log(
    `  contenido bbox [${minX}..${maxX}]x[${minY}..${maxY}], mitad=${contentHalf.toFixed(1)}px, esquina fuera de safe circle=${outsideSafe}`,
  )

  const bboxOk =
    minX >= SAFE_BOX && minY >= SAFE_BOX && maxX <= CANVAS - SAFE_BOX && maxY <= CANVAS - SAFE_BOX
  if (!bboxOk) {
    throw new Error(`maskable: el contenido sale del cajón central [${SAFE_BOX}..${CANVAS - SAFE_BOX}]`)
  }
  if (outsideSafe > 0) {
    throw new Error(`maskable: ${outsideSafe} píxeles de contenido fuera del círculo seguro (radio ${SAFE_RADIUS})`)
  }
  console.log('  safe zone maskable OK (todo el contenido dentro del círculo de radio 40%)')
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err)
  process.exit(1)
})
