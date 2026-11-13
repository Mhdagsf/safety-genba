/**
 * PT. FUJISEAT INDONESIA - Safety Genba D26A
 * 100% Offline Interactive Chart Engine (High-DPI Canvas & DOM)
 */
(function (window) {
    'use strict';

    // Shared floating tooltip element
    let tooltipEl = null;
    function getTooltip() {
        if (!tooltipEl) {
            tooltipEl = document.createElement('div');
            tooltipEl.className = 'genba-chart-tooltip';
            tooltipEl.style.cssText = [
                'position: fixed',
                'pointer-events: none',
                'z-index: 9999',
                'background: rgba(15, 23, 42, 0.95)',
                'color: #f8fafc',
                'padding: 8px 12px',
                'border-radius: 8px',
                'font-size: 12px',
                'line-height: 1.45',
                'box-shadow: 0 10px 25px -5px rgba(0,0,0,0.35)',
                'border: 1px solid rgba(148, 163, 184, 0.25)',
                'opacity: 0',
                'transition: opacity 0.12s ease, transform 0.12s ease',
                'transform: translateY(4px)'
            ].join(';');
            document.body.appendChild(tooltipEl);
        }
        return tooltipEl;
    }

    function showTooltip(evt, htmlContent) {
        const tt = getTooltip();
        tt.innerHTML = htmlContent;
        tt.style.opacity = '1';
        tt.style.transform = 'translateY(0)';
        const pad = 14;
        let x = evt.clientX + pad;
        let y = evt.clientY - pad;
        const rect = tt.getBoundingClientRect();
        if (x + rect.width > window.innerWidth - 12) {
            x = evt.clientX - rect.width - pad;
        }
        if (y + rect.height > window.innerHeight - 12) {
            y = window.innerHeight - rect.height - 12;
        }
        if (y < 12) y = 12;
        tt.style.left = x + 'px';
        tt.style.top = y + 'px';
    }

    function hideTooltip() {
        const tt = getTooltip();
        tt.style.opacity = '0';
        tt.style.transform = 'translateY(4px)';
    }

    function setupHiDPICanvas(canvas, heightPx) {
        const dpr = window.devicePixelRatio || 1;
        const parentWidth = Math.max(240, canvas.parentElement.clientWidth || 360);
        const h = heightPx || parseInt(canvas.getAttribute('height'), 10) || 240;
        canvas.style.width = parentWidth + 'px';
        canvas.style.height = h + 'px';
        canvas.width = Math.round(parentWidth * dpr);
        canvas.height = Math.round(h * dpr);
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);
        return { ctx, width: parentWidth, height: h };
    }

    function roundRect(ctx, x, y, w, h, r) {
        if (w <= 0 || h <= 0) return;
        const radius = Math.min(r, w / 2, h / 2);
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + w - radius, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
        ctx.lineTo(x + w, y + h - radius);
        ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
        ctx.lineTo(x + radius, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
    }

    // =========================================================================
    // 1. GROUPED / STACKED BAR CHART PER LINE PRODUKSI
    // =========================================================================
    function renderLineBarChart(canvasId, linesData, options) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !Array.isArray(linesData)) return;
        options = options || {};

        let hitBoxes = [];
        let hoveredIndex = -1;

        function draw(progress) {
            const { ctx, width, height } = setupHiDPICanvas(canvas, options.height || 245);
            ctx.clearRect(0, 0, width, height);

            const padTop = 28;
            const padBottom = 36;
            const padLeft = 36;
            const padRight = 16;
            const chartW = width - padLeft - padRight;
            const chartH = height - padTop - padBottom;

            const maxVal = Math.max(4, ...linesData.map(d => d.total || 0));
            const steps = 4;
            const stepVal = Math.ceil(maxVal / steps);
            const yMax = stepVal * steps;

            // Grid lines & Y-axis labels
            ctx.font = '500 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';

            for (let i = 0; i <= steps; i++) {
                const val = stepVal * i;
                const y = padTop + chartH - (val / yMax) * chartH;
                ctx.strokeStyle = i === 0 ? '#cbd5e1' : '#f1f5f9';
                ctx.lineWidth = i === 0 ? 1.5 : 1;
                ctx.beginPath();
                ctx.moveTo(padLeft, y);
                ctx.lineTo(width - padRight, y);
                ctx.stroke();

                ctx.fillStyle = '#64748b';
                ctx.fillText(String(val), padLeft - 8, y);
            }

            const count = linesData.length || 1;
            const slotW = chartW / count;
            const barW = Math.min(38, Math.max(16, slotW * 0.54));

            hitBoxes = [];

            linesData.forEach((item, idx) => {
                const centerX = padLeft + slotW * idx + slotW / 2;
                const x = centerX - barW / 2;

                // Highlight slot on hover
                if (idx === hoveredIndex) {
                    ctx.fillStyle = 'rgba(37, 99, 235, 0.06)';
                    roundRect(ctx, padLeft + slotW * idx + 3, padTop, slotW - 6, chartH, 6);
                    ctx.fill();
                }

                const okH = ((item.ok || 0) / yMax) * chartH * progress;
                const progH = ((item.on_progress || 0) / yMax) * chartH * progress;
                const totalH = okH + progH;

                const baseY = padTop + chartH;

                // Draw OK segment (bottom)
                if (okH > 0) {
                    ctx.fillStyle = '#10b981';
                    roundRect(ctx, x, baseY - okH, barW, okH, progH > 0 ? 2 : 5);
                    ctx.fill();
                }

                // Draw On Progress segment (top)
                if (progH > 0) {
                    ctx.fillStyle = item.overdue > 0 ? '#dc2626' : '#f97316';
                    roundRect(ctx, x, baseY - totalH, barW, progH, 5);
                    ctx.fill();
                }

                // Empty bar indicator
                if ((item.total || 0) === 0) {
                    ctx.fillStyle = '#e2e8f0';
                    roundRect(ctx, x, baseY - 3, barW, 3, 1.5);
                    ctx.fill();
                }

                // Value label above bar
                if (item.total > 0 && progress > 0.85) {
                    ctx.fillStyle = '#0f172a';
                    ctx.font = '700 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(String(item.total), centerX, baseY - totalH - 4);
                }

                // X-axis label
                ctx.fillStyle = idx === hoveredIndex ? '#1e3a8a' : '#334155';
                ctx.font = (idx === hoveredIndex ? '700' : '600') + ' 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillText(item.line, centerX, baseY + 10);

                hitBoxes.push({
                    x: padLeft + slotW * idx,
                    y: padTop,
                    w: slotW,
                    h: chartH + padBottom,
                    item: item,
                    idx: idx
                });
            });
        }

        // Smooth animation
        let start = null;
        function animate(ts) {
            if (!start) start = ts;
            const elapsed = ts - start;
            const p = Math.min(1, elapsed / 450);
            const eased = 1 - Math.pow(1 - p, 3);
            draw(eased);
            if (p < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);

        // Mouse interactions
        canvas.onmousemove = function (e) {
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            let found = -1;
            let hitItem = null;
            for (const b of hitBoxes) {
                if (mx >= b.x && mx <= b.x + b.w && my >= b.y && my <= b.y + b.h) {
                    found = b.idx;
                    hitItem = b.item;
                    break;
                }
            }
            if (found !== hoveredIndex) {
                hoveredIndex = found;
                draw(1);
            }
            if (hitItem) {
                canvas.style.cursor = 'default';
                showTooltip(e, `
                    <div style="font-weight:700; margin-bottom:4px; color:#93c5fd; border-bottom:1px solid rgba(255,255,255,0.15); padding-bottom:3px;">
                        Line ${hitItem.line}
                    </div>
                    <div>Total Temuan: <strong>${hitItem.total}</strong></div>
                    <div style="color:#4ade80;">&#9679; Selesai (O): <strong>${hitItem.ok}</strong> (${hitItem.pct}%)</div>
                    <div style="color:#fb923c;">&#9679; Belum Selesai (X): <strong>${hitItem.on_progress}</strong></div>
                    ${hitItem.overdue > 0 ? `<div style="color:#f87171;">&#9888; Overdue: <strong>${hitItem.overdue}</strong></div>` : ''}
                `);
            } else {
                canvas.style.cursor = 'default';
                hideTooltip();
            }
        };

        canvas.onmouseleave = function () {
            hoveredIndex = -1;
            draw(1);
            hideTooltip();
        };

        window.addEventListener('resize', function () {
            draw(1);
        });
    }

    // =========================================================================
    // 2. DONUT CHART STATUS JUDGEMENT (O / X / OVERDUE)
    // =========================================================================
    function renderStatusDonut(canvasId, summary, options) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !summary) return;
        options = options || {};
        const mode = (options.mode || 'ALL').toUpperCase();

        const total = summary.total || 0;
        const okVal = summary.ok || 0;
        const xTotalVal = summary.on_progress || 0;
        const ontimeVal = summary.ontime_progress || 0;
        const overdueVal = summary.overdue || 0;

        let slices = [];
        let centerPct = '0%';
        let centerSub = 'SELESAI (0/0)';
        let centerColor = '#0f172a';

        if (mode === 'O') {
            const p = total > 0 ? Math.round((okVal / total) * 1000) / 10 : 0;
            centerPct = p + '%';
            centerSub = 'SELESAI (' + okVal + '/' + total + ')';
            centerColor = '#059669';
            slices = [
                { label: 'Selesai (O)', value: okVal, color: '#10b981' },
                { label: 'Lainnya', value: Math.max(0, total - okVal), color: '#e2e8f0' }
            ];
        } else if (mode === 'X') {
            const p = total > 0 ? Math.round((xTotalVal / total) * 1000) / 10 : 0;
            centerPct = p + '%';
            centerSub = 'BELUM (' + xTotalVal + '/' + total + ')';
            centerColor = '#d97706';
            slices = [
                { label: 'Belum Selesai (X)', value: xTotalVal, color: '#f59e0b' },
                { label: 'Selesai (O)', value: Math.max(0, total - xTotalVal), color: '#e2e8f0' }
            ];
        } else if (mode === 'OVERDUE') {
            const p = total > 0 ? Math.round((overdueVal / total) * 1000) / 10 : 0;
            centerPct = p + '%';
            centerSub = 'OVERDUE (' + overdueVal + '/' + total + ')';
            centerColor = '#dc2626';
            slices = [
                { label: 'Overdue (Terlambat)', value: overdueVal, color: '#ef4444' },
                { label: 'Lainnya', value: Math.max(0, total - overdueVal), color: '#e2e8f0' }
            ];
        } else {
            centerPct = (summary.pct_closed || 0) + '%';
            centerSub = 'SELESAI (' + okVal + '/' + total + ')';
            centerColor = '#0f172a';
            slices = [
                { label: 'Selesai (O)', value: okVal, color: '#10b981' },
                { label: 'On Progress (X)', value: ontimeVal, color: '#f59e0b' },
                { label: 'Overdue (Terlambat)', value: overdueVal, color: '#ef4444' }
            ];
        }

        let hoveredSlice = -1;
        let arcMeta = [];

        function draw(progress) {
            const { ctx, width, height } = setupHiDPICanvas(canvas, options.height || 220);
            ctx.clearRect(0, 0, width, height);

            const cx = width / 2;
            const cy = height / 2;
            const outerR = Math.min(width, height) * 0.40;
            const innerR = outerR * 0.64;

            arcMeta = [];

            if (total === 0) {
                ctx.beginPath();
                ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
                ctx.arc(cx, cy, innerR, Math.PI * 2, 0, true);
                ctx.fillStyle = '#e2e8f0';
                ctx.fill();
            } else {
                let startAngle = -Math.PI / 2;
                slices.forEach((s, idx) => {
                    if (s.value <= 0) return;
                    const sliceAngle = (s.value / total) * (Math.PI * 2) * progress;
                    const endAngle = startAngle + sliceAngle;
                    const isHover = idx === hoveredSlice;
                    const rOut = isHover ? outerR + 4 : outerR;

                    ctx.beginPath();
                    ctx.arc(cx, cy, rOut, startAngle, endAngle);
                    ctx.arc(cx, cy, innerR, endAngle, startAngle, true);
                    ctx.closePath();
                    ctx.fillStyle = s.color;
                    ctx.fill();

                    ctx.lineWidth = 2;
                    ctx.strokeStyle = '#ffffff';
                    ctx.stroke();

                    arcMeta.push({ idx, startAngle, endAngle, slice: s, cx, cy, innerR, outerR: rOut });
                    startAngle = endAngle;
                });
            }

            // Center text
            ctx.fillStyle = centerColor;
            ctx.font = '800 22px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(centerPct, cx, cy - 8);

            ctx.fillStyle = '#64748b';
            ctx.font = '600 10px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
            ctx.fillText(centerSub, cx, cy + 13);
        }

        let start = null;
        function animate(ts) {
            if (!start) start = ts;
            const p = Math.min(1, (ts - start) / 480);
            const eased = 1 - Math.pow(1 - p, 3);
            draw(eased);
            if (p < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);

        canvas.onmousemove = function (e) {
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;

            let found = -1;
            let hitSlice = null;

            for (const m of arcMeta) {
                const dx = mx - m.cx;
                const dy = my - m.cy;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist >= m.innerR && dist <= m.outerR + 6) {
                    let angle = Math.atan2(dy, dx);
                    if (angle < -Math.PI / 2) angle += Math.PI * 2;
                    if (angle >= m.startAngle && angle <= m.endAngle) {
                        found = m.idx;
                        hitSlice = m.slice;
                        break;
                    }
                }
            }

            if (found !== hoveredSlice) {
                hoveredSlice = found;
                draw(1);
            }

            if (hitSlice && total > 0) {
                const pct = ((hitSlice.value / total) * 100).toFixed(1);
                canvas.style.cursor = 'default';
                showTooltip(e, `
                    <div style="font-weight:700; color:${hitSlice.color};">${hitSlice.label}</div>
                    <div>Jumlah: <strong>${hitSlice.value}</strong> temuan (${pct}%)</div>
                `);
            } else {
                canvas.style.cursor = 'default';
                hideTooltip();
            }
        };

        canvas.onmouseleave = function () {
            hoveredSlice = -1;
            draw(1);
            hideTooltip();
        };

        window.addEventListener('resize', function () {
            draw(1);
        });
    }

    // =========================================================================
    // 3. TIMELINE TREND AREA CHART (TEMUAN VS SELESAI)
    // =========================================================================
    function renderTrendChart(canvasId, trendData, options) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !Array.isArray(trendData)) return;
        options = options || {};

        let hoveredIdx = -1;
        let pointsMeta = [];

        function draw(progress) {
            const { ctx, width, height } = setupHiDPICanvas(canvas, options.height || 235);
            ctx.clearRect(0, 0, width, height);

            const padTop = 24;
            const padBottom = 34;
            const padLeft = 34;
            const padRight = 18;
            const chartW = width - padLeft - padRight;
            const chartH = height - padTop - padBottom;

            if (trendData.length === 0) {
                ctx.fillStyle = '#94a3b8';
                ctx.font = '500 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('Belum ada data tren pada periode ini', width / 2, height / 2);
                return;
            }

            const maxVal = Math.max(4, ...trendData.map(d => d.total || 0));
            const steps = 4;
            const stepVal = Math.ceil(maxVal / steps);
            const yMax = stepVal * steps;

            // Grid
            ctx.font = '500 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            for (let i = 0; i <= steps; i++) {
                const val = stepVal * i;
                const y = padTop + chartH - (val / yMax) * chartH;
                ctx.strokeStyle = i === 0 ? '#cbd5e1' : '#f1f5f9';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(padLeft, y);
                ctx.lineTo(width - padRight, y);
                ctx.stroke();
                ctx.fillStyle = '#64748b';
                ctx.fillText(String(val), padLeft - 8, y);
            }

            const n = trendData.length;
            const getX = (i) => n === 1 ? padLeft + chartW / 2 : padLeft + (i / (n - 1)) * chartW;
            const getYTotal = (i) => padTop + chartH - ((trendData[i].total || 0) / yMax) * chartH * progress;
            const getYOk = (i) => padTop + chartH - ((trendData[i].ok || 0) / yMax) * chartH * progress;

            // Area fill for Total
            ctx.beginPath();
            ctx.moveTo(getX(0), padTop + chartH);
            for (let i = 0; i < n; i++) ctx.lineTo(getX(i), getYTotal(i));
            ctx.lineTo(getX(n - 1), padTop + chartH);
            ctx.closePath();
            const gradTotal = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
            gradTotal.addColorStop(0, 'rgba(37, 99, 235, 0.22)');
            gradTotal.addColorStop(1, 'rgba(37, 99, 235, 0.01)');
            ctx.fillStyle = gradTotal;
            ctx.fill();

            // Line for Total
            ctx.beginPath();
            for (let i = 0; i < n; i++) {
                if (i === 0) ctx.moveTo(getX(i), getYTotal(i));
                else ctx.lineTo(getX(i), getYTotal(i));
            }
            ctx.strokeStyle = '#2563eb';
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Line for OK
            ctx.beginPath();
            for (let i = 0; i < n; i++) {
                if (i === 0) ctx.moveTo(getX(i), getYOk(i));
                else ctx.lineTo(getX(i), getYOk(i));
            }
            ctx.strokeStyle = '#10b981';
            ctx.lineWidth = 2.2;
            ctx.setLineDash([4, 3]);
            ctx.stroke();
            ctx.setLineDash([]);

            pointsMeta = [];
            for (let i = 0; i < n; i++) {
                const px = getX(i);
                const pyTot = getYTotal(i);
                const pyOk = getYOk(i);

                if (i === hoveredIdx) {
                    ctx.beginPath();
                    ctx.moveTo(px, padTop);
                    ctx.lineTo(px, padTop + chartH);
                    ctx.strokeStyle = 'rgba(100, 116, 139, 0.35)';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }

                // Point Total
                ctx.beginPath();
                ctx.arc(px, pyTot, i === hoveredIdx ? 5 : 3.5, 0, Math.PI * 2);
                ctx.fillStyle = '#2563eb';
                ctx.fill();
                ctx.lineWidth = 1.5;
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();

                // Point OK
                ctx.beginPath();
                ctx.arc(px, pyOk, i === hoveredIdx ? 4.5 : 3, 0, Math.PI * 2);
                ctx.fillStyle = '#10b981';
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();

                // X label (show max ~6 labels to avoid crowding)
                const stride = Math.max(1, Math.ceil(n / 6));
                if (i % stride === 0 || i === n - 1) {
                    const shortDate = (trendData[i].date || '').slice(5); // MM-DD
                    ctx.fillStyle = '#475569';
                    ctx.font = '600 10px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'top';
                    ctx.fillText(shortDate || trendData[i].date, px, padTop + chartH + 10);
                }

                pointsMeta.push({ idx: i, x: px, item: trendData[i] });
            }
        }

        let start = null;
        function animate(ts) {
            if (!start) start = ts;
            const p = Math.min(1, (ts - start) / 450);
            draw(1 - Math.pow(1 - p, 3));
            if (p < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);

        canvas.onmousemove = function (e) {
            if (!pointsMeta.length) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            let closest = -1;
            let minDist = 9999;
            pointsMeta.forEach(p => {
                const d = Math.abs(mx - p.x);
                if (d < minDist && d < 36) {
                    minDist = d;
                    closest = p.idx;
                }
            });
            if (closest !== hoveredIdx) {
                hoveredIdx = closest;
                draw(1);
            }
            if (closest >= 0) {
                const d = pointsMeta[closest].item;
                showTooltip(e, `
                    <div style="font-weight:700; color:#93c5fd; margin-bottom:3px;">Tanggal: ${d.date}</div>
                    <div>&#9679; Total Temuan: <strong>${d.total}</strong></div>
                    <div style="color:#4ade80;">&#9679; Selesai (O): <strong>${d.ok}</strong></div>
                    <div style="color:#fb923c;">&#9679; Belum Selesai (X): <strong>${d.on_progress}</strong></div>
                `);
            } else {
                hideTooltip();
            }
        };

        canvas.onmouseleave = function () {
            hoveredIdx = -1;
            draw(1);
            hideTooltip();
        };

        window.addEventListener('resize', function () {
            draw(1);
        });
    }

    window.GenbaCharts = {
        renderLineBarChart: renderLineBarChart,
        renderStatusDonut: renderStatusDonut,
        renderTrendChart: renderTrendChart
    };
})(window);

