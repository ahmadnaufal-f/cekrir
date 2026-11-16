// Synthesized Chromium touch input, not DOM dispatch or a physical-device test.
async function touchDrag(page, session, { x, y, dx = 0, dy, cancel = false }) {
  await session.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x, y, id: 1 }],
  })
  for (let step = 1; step <= 8; step++) {
    await session.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ x: x + (dx * step) / 8, y: y + (dy * step) / 8, id: 1 }],
    })
    await page.waitForTimeout(20)
  }
  await session.send('Input.dispatchTouchEvent', {
    type: cancel ? 'touchCancel' : 'touchEnd',
    touchPoints: [],
  })
}

async function pullRefresh(page, session) {
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForFunction(
    () =>
      document
        .querySelector('.pull-to-refresh__content')
        ?.getAttribute('aria-busy') === 'false',
  )
  const box = await page.locator('.pull-to-refresh').boundingBox()
  await touchDrag(page, session, { x: box.x + 36, y: box.y + 18, dy: 160 })
}
module.exports = { touchDrag, pullRefresh }
