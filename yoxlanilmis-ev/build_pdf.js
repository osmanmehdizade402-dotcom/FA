// Yoxlanılmış Ev PDF-lərini qurur (Chromium/Playwright ilə).
//   node yoxlanilmis-ev/build_pdf.js            -> boş yoxlama vərəqi + partnyor təqdimatı
//   node yoxlanilmis-ev/build_pdf.js ev.json    -> ev.json məlumatı ilə doldurulmuş vərəq
// ev.json: {"slug","number","date","title","place","size","rooms"}
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const HERE = __dirname;
const OUT = path.join(HERE, 'out');
const BLANK = { number: '________', date: '____.____.______', title: '', place: '', size: '', rooms: '' };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const jobs = [['partnyor-teqdimati.html', null, 'partnyor-teqdimati.pdf']];
  if (process.argv[2]) {
    const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
    jobs.push(['yoxlama-veraqi.html', { ...BLANK, ...data }, `yoxlama-veraqi-${data.slug || 'ev'}.pdf`]);
  } else {
    jobs.push(['yoxlama-veraqi.html', BLANK, 'yoxlama-veraqi-bos.pdf']);
  }
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [src, data, name] of jobs) {
    let file = path.join(HERE, src);
    if (data) {
      let html = fs.readFileSync(file, 'utf8');
      for (const [k, v] of Object.entries(data)) html = html.split(`{{${k}}}`).join(String(v));
      file = path.join(HERE, `.tmp-${name}.html`); // same folder so relative font/logo paths resolve
      fs.writeFileSync(file, html);
    }
    await page.goto('file://' + file);
    await page.waitForLoadState('networkidle');
    await page.pdf({ path: path.join(OUT, name), format: 'A4', printBackground: true, preferCSSPageSize: true });
    if (data) fs.unlinkSync(file);
    console.log(path.join(OUT, name));
  }
  await browser.close();
})();
