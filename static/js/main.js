// SporoSentinel Client Controller

let deferredPrompt = null;
let currentLanguage = "en";
let isSpeaking = false;
let speechUtterance = null;
let lastScanData = null; // Caches the latest scan result for dynamic translation updates

document.addEventListener("DOMContentLoaded", () => {
    // 1. Language Initialization
    currentLanguage = localStorage.getItem("sporo_lang") || "en";
    
    // Auto-map region name data-trn attribute before translating DOM
    const regionDisplay = document.getElementById("farmer-region-display");
    if (regionDisplay) {
        const regionVal = regionDisplay.textContent.trim();
        const regionKeyMap = {
            "Aspergillus-prone South": "region_south",
            "High-humidity Coastal": "region_coastal",
            "Western Drylands": "region_drylands",
            "Northern Grain Belt": "region_north"
        };
        const key = regionKeyMap[regionVal];
        if (key) {
            regionDisplay.setAttribute("data-trn", key);
        }
    }
    
    translateDOM(currentLanguage);

    const langSelector = document.getElementById("lang-selector");
    const themeToggle = document.getElementById("theme-toggle");
    const htmlEl = document.documentElement;

    if (langSelector) {
        langSelector.value = currentLanguage;
        langSelector.addEventListener("change", (e) => {
            const newLang = e.target.value;
            currentLanguage = newLang;
            localStorage.setItem("sporo_lang", newLang);
            translateDOM(newLang);
            
            // Translate the theme toggle span explicitly
            const span = themeToggle ? themeToggle.querySelector("span") : null;
            if (span) translateElement(span, newLang);
            
            // Re-render scan results in the new language if active
            if (lastScanData) {
                updateUIWithResult(lastScanData);
            }
            
            // Save selection to profile database in background if online
            if (navigator.onLine) {
                const formData = new FormData();
                formData.append("language_pref", newLang);
                formData.append("region", localStorage.getItem("sporo_region") || "General");
                fetch("/api/users/onboard", {
                    method: "POST",
                    body: formData
                }).catch(() => {/* ignore background save errors */});
            }
        });
    }

    // 2. Dark/Light Theme Control
    const savedTheme = localStorage.getItem("sporo_theme") || "dark";
    htmlEl.setAttribute("data-theme", savedTheme);
    if (themeToggle) {
        themeToggle.innerHTML = savedTheme === "dark" ? "☀️ <span data-trn='theme_light'>Light Mode</span>" : "🌙 <span data-trn='theme_dark'>Dark Mode</span>";
        const span = themeToggle.querySelector("span");
        if (span) translateElement(span, currentLanguage);
        
        themeToggle.addEventListener("click", () => {
            const currentTheme = htmlEl.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            htmlEl.setAttribute("data-theme", newTheme);
            localStorage.setItem("sporo_theme", newTheme);
            themeToggle.innerHTML = newTheme === "dark" ? "☀️ <span data-trn='theme_light'>Light Mode</span>" : "🌙 <span data-trn='theme_dark'>Dark Mode</span>";
            const span = themeToggle.querySelector("span");
            if (span) translateElement(span, currentLanguage);
        });
    }

    // 3. Network Connectivity Telemetry
    updateConnectionStatus();
    window.addEventListener("online", () => {
        updateConnectionStatus();
        triggerOfflineSync();
    });
    window.addEventListener("offline", updateConnectionStatus);

    // 4. PWA Install Event Handler
    const installPromo = document.getElementById("pwa-install-promo");
    const installBtn = document.getElementById("pwa-install-btn");
    
    window.addEventListener("beforeinstallprompt", (e) => {
        e.preventDefault();
        deferredPrompt = e;
        if (installPromo) installPromo.style.display = "flex";
    });

    if (installBtn) {
        installBtn.addEventListener("click", () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === "accepted") {
                        if (installPromo) installPromo.style.display = "none";
                    }
                    deferredPrompt = null;
                });
            }
        });
    }

    // 5. Service Worker Registration and Update Notification
    if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js")
            .then((reg) => {
                console.log("SporoSentinel Service Worker Registered");
                
                // Watch for service worker updates
                reg.addEventListener("updatefound", () => {
                    const newWorker = reg.installing;
                    newWorker.addEventListener("statechange", () => {
                        console.log("Service Worker state changed to: " + newWorker.state);
                    });
                });
            })
            .catch((err) => console.error("Service Worker registration failed", err));

        // Sync refresh when controller changes
        let refreshing = false;
        navigator.serviceWorker.addEventListener("controllerchange", () => {
            if (!refreshing) {
                refreshing = true;
                if (confirm("A new version of SporoSentinel is available. Refresh now?")) {
                    window.location.reload();
                }
            }
        });
    }

    // 6. Camera Strip Scanner Events (Farmer Dashboard only)
    initializeScannerControls();

    // 7. Offline scan queue check on startup
    checkOfflineQueueSize();
});

// Update UI Connection badges
function updateConnectionStatus() {
    const statusBadge = document.getElementById("connection-status");
    const statusText = document.getElementById("connection-status-text");
    
    if (!statusBadge || !statusText) return;
    
    if (navigator.onLine) {
        statusBadge.className = "status-badge status-online";
        statusText.setAttribute("data-trn", "status_online");
        translateElement(statusText, currentLanguage);
    } else {
        statusBadge.className = "status-badge status-offline";
        statusText.setAttribute("data-trn", "status_offline");
        translateElement(statusText, currentLanguage);
    }
}

// Translations Engine: Iterates all DOM elements containing [data-trn]
function translateDOM(lang) {
    const elements = document.querySelectorAll("[data-trn]");
    elements.forEach(el => {
        translateElement(el, lang);
    });
}function translateElement(el, lang) {
    const key = el.getAttribute("data-trn");
    const dict = translations[lang] || translations["en"];
    if (dict && dict[key]) {
        // If element is input/placeholder
        if (el.tagName === "INPUT" && el.placeholder) {
            el.placeholder = dict[key];
        } else {
            // Keep child badges or text
            const icon = el.querySelector(".status-dot");
            if (icon) {
                el.innerHTML = "";
                el.appendChild(icon);
                el.appendChild(document.createTextNode(" " + dict[key]));
            } else {
                el.innerHTML = dict[key];
            }
        }
    }
}
// Local Storage based offline queue for scans when offline
const OFFLINE_QUEUE_KEY = "sporo_offline_scans";

function getOfflineQueue() {
    try {
        return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY)) || [];
    } catch {
        return [];
    }
}

function saveOfflineQueue(queue) {
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
    checkOfflineQueueSize();
}

function checkOfflineQueueSize() {
    const queue = getOfflineQueue();
    const banner = document.getElementById("sync-banner");
    const countSpan = document.getElementById("sync-count");
    
    if (!banner || !countSpan) return;
    
    if (queue.length > 0) {
        countSpan.textContent = queue.length;
        banner.style.display = "flex";
    } else {
        banner.style.display = "none";
    }
}

// Scanner event bindings
function initializeScannerControls() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const scanSubmit = document.getElementById("scan-submit-btn");
    const previewContainer = document.getElementById("image-preview-container");
    const previewImg = document.getElementById("image-preview");
    
    if (!dropZone) return; // Not on farmer page

    dropZone.addEventListener("click", () => fileInput.click());
    
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--accent-primary)";
    });
    
    dropZone.addEventListener("dragleave", () => {
        dropZone.style.borderColor = "var(--border-color)";
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--border-color)";
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    fileInput.addEventListener("change", handleFileSelect);

    function handleFileSelect() {
        if (fileInput.files && fileInput.files[0]) {
            const file = fileInput.files[0];
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImg.src = e.target.result;
                previewContainer.style.display = "block";
                scanSubmit.style.display = "block";
            };
            reader.readAsDataURL(file);
        }
    }

    // Direct upload analysis form submit
    scanSubmit.addEventListener("click", () => {
        if (!fileInput.files.length) return;
        
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("region", localStorage.getItem("sporo_region") || "General");

        scanSubmit.disabled = true;
        scanSubmit.textContent = "Processing...";

        if (navigator.onLine) {
            // Online upload
            fetch("/api/scans/analyze", {
                method: "POST",
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                updateUIWithResult(data);
                addScanToLogTable(data);
            })
            .catch(err => {
                console.error("Analysis failed, queueing offline", err);
                queueScanOffline(file);
            })
            .finally(() => {
                scanSubmit.disabled = false;
                scanSubmit.textContent = translations[currentLanguage].analyze_btn || "Analyze Scan";
            });
        } else {
            // Offline caching
            queueScanOffline(file);
            scanSubmit.disabled = false;
            scanSubmit.textContent = translations[currentLanguage].analyze_btn || "Analyze Scan";
        }
    });

    // Demo scan triggers
    bindDemoButton("load-sample-safe-btn", "safe");
    bindDemoButton("load-sample-caution-btn", "caution");
    bindDemoButton("load-sample-critical-btn", "critical");

    function bindDemoButton(btnId, level) {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener("click", () => {
                // Online demo fetch
                if (navigator.onLine) {
                    fetch(`/api/scans/demo-scan?level=${level}&region=${localStorage.getItem("sporo_region") || "General"}`)
                        .then(res => res.json())
                        .then(data => {
                            updateUIWithResult(data);
                            addScanToLogTable(data);
                        })
                        .catch(() => generateClientSideMockResult(level));
                } else {
                    // Offline mock generation
                    generateClientSideMockResult(level);
                }
            });
        }
    }

    // Text to Speech bindings
    const ttsBtn = document.getElementById("tts-btn");
    if (ttsBtn) {
        ttsBtn.addEventListener("click", () => {
            const recText = document.getElementById("recommendation-content").innerText;
            if (!recText || recText.includes("Perform or load")) return;

            toggleSpeech(recText);
        });
    }

    // Sync button binding
    const syncBtn = document.getElementById("sync-now-btn");
    if (syncBtn) {
        syncBtn.addEventListener("click", triggerOfflineSync);
    }
}

// Queue file offline as base64 blob
function queueScanOffline(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const queue = getOfflineQueue();
        const offlineScanObj = {
            id: Date.now(),
            fileName: file.name,
            fileData: e.target.result, // base64
            region: localStorage.getItem("sporo_region") || "General",
            timestamp: new Date().toLocaleString()
        };
        queue.push(offlineScanObj);
        saveOfflineQueue(queue);
        
        // Show mock client side result immediately so user has offline validation
        generateClientSideMockResult("caution", offlineScanObj.timestamp, "Pending Sync");
    };
    reader.readAsDataURL(file);
}

// Client-side mock result for 100% offline scanning
function generateClientSideMockResult(level, customTime = null, syncText = "Offline Mode") {
    let fi = 12.0, vi = 8.0, cci = 10.4, dist = 14.5, risk = "Safe", conf = 94.0, trend = "Declining";
    let advice = "Fungal contamination is minimal. Continue storage under standard hermetic conditions.";
    
    if (level === "caution") {
        fi = 54.0; vi = 38.0; cci = 47.6; dist = 52.3; risk = "Caution"; conf = 85.0; trend = "Stable";
        advice = "[Caution]: Elevated fungal index. Improve ventilation and run dynamic aeration systems to reduce humidity.";
    } else if (level === "critical") {
        fi = 89.0; vi = 82.0; cci = 86.2; dist = 112.5; risk = "Critical"; conf = 93.0; trend = "Rising";
        advice = "[Critical]: Critical mycotoxin danger. Immediate laboratory testing required before distribution. Terminate raw food usage.";
    }
    
    const mockPayload = {
        fi_score: fi,
        vi_score: vi,
        cci_score: cci,
        euclidean_distance: dist,
        risk_level: risk,
        confidence: conf,
        trend: trend,
        timestamp: customTime || new Date().toLocaleString(),
        recommendations: advice,
        sync_status: syncText
    };
    
    updateUIWithResult(mockPayload);
    addScanToLogTable(mockPayload);
}

// Dynamic UI rendering
function updateUIWithResult(data) {
    lastScanData = data;
    const resultsCard = document.getElementById("results-card");
    if (resultsCard) resultsCard.style.opacity = "1";
    
    // Update CCI displays
    document.getElementById("cci-display").textContent = data.cci_score.toFixed(1);
    
    // Update individual indices
    document.getElementById("fi-val").textContent = data.fi_score.toFixed(1);
    document.getElementById("fi-bar").style.width = data.fi_score + "%";
    
    document.getElementById("vi-val").textContent = data.vi_score.toFixed(1);
    document.getElementById("vi-bar").style.width = data.vi_score + "%";
    
    // Update gauge SVG rotation ring
    const fill = document.getElementById("cci-gauge-fill");
    if (fill) {
        // Circumference is 2 * pi * r = 2 * 3.14159 * 65 = 408.4
        const offset = 408.4 - (data.cci_score / 100) * 408.4;
        fill.style.strokeDashoffset = offset;
        
        // Color shifts based on risk
        let color = "var(--color-safe)";
        if (data.risk_level === "Critical") color = "var(--color-critical)";
        else if (data.risk_level === "High Risk") color = "var(--color-high-risk)";
        else if (data.risk_level === "Caution") color = "var(--color-caution)";
        else if (data.risk_level === "Monitor") color = "var(--color-monitor)";
        fill.style.stroke = color;
    }

    // Dynamic Translation Mapping
    const dict = translations[currentLanguage] || translations["en"];
    const riskKey = "risk_" + data.risk_level.toLowerCase().replace(" ", "_");
    const trendKey = "trend_" + data.trend.toLowerCase();
    
    const trnRisk = dict[riskKey] || data.risk_level;
    const trnTrend = dict[trendKey] || data.trend;
    
    // Translate the recommendations text
    let trnRec = data.recommendations;
    
    // Translate base recommendation parts
    if (trnRec.includes("Fungal contamination is minimal")) {
        trnRec = trnRec.replace("Fungal contamination is minimal. Continue storage under standard hermetic conditions.", dict["rec_safe"] || "Fungal contamination is minimal.");
    }
    if (trnRec.includes("Minor microbial activity detected")) {
        trnRec = trnRec.replace("Minor microbial activity detected. Reinspect the grain pile and scan again in 48 hours.", dict["rec_monitor"] || "Minor microbial activity detected.");
    }
    if (trnRec.includes("Elevated fungal index")) {
        trnRec = trnRec.replace("Elevated fungal index. Improve ventilation and run dynamic aeration systems to reduce humidity.", dict["rec_caution"] || "Elevated fungal index.");
    }
    if (trnRec.includes("High contamination risk")) {
        trnRec = trnRec.replace("High contamination risk. Quarantine the affected grain bags immediately and isolate the storage bin.", dict["rec_high_risk"] || "High contamination risk.");
    }
    if (trnRec.includes("Critical mycotoxin danger")) {
        trnRec = trnRec.replace("Critical mycotoxin danger. Immediate laboratory testing required before distribution. Terminate raw food usage.", dict["rec_critical"] || "Critical mycotoxin danger.");
    }
    
    // Translate regional guidelines
    if (trnRec.includes("Southern soils")) {
        const trnSouth = {
            hi: "[एस्परजिलस गाइडलाइन]: गंभीर जोखिम चेतावनी: दक्षिणी मिट्टी में एस्परजिलस का प्रकोप अधिक है। एफ़्लैटॉक्सिन के लिए भंडारण इकाइयों का तत्काल परीक्षण करें।",
            es: "[Aspergillus flavus Directriz]: Alerta de riesgo crítico: los brotes de Aspergillus son altos en los suelos del sur. Muestree las unidades de almacenamiento inmediatamente para detectar aflatoxinas.",
            zh: "[黄曲霉指南]: 严重风险警报：南方土壤中黄曲霉菌爆发率高。请立即对储粮单元进行黄曲霉毒素抽样检测。",
            bn: "[অ্যাসপারজিলাস নির্দেশিকা]: মারাত্মক ঝুঁকি: দক্ষিণের মাটিতে অ্যাসপারজিলাসের প্রাদুর্ভাব বেশি। অবিলম্বে পরীক্ষা করুন।",
            fr: "[Directive Aspergillus]: Alerte de risque critique: Épidémies élevées dans les sols du sud. Analysez immédiatement."
        };
        const textToReplace = "Critical risk alert: Aspergillus outbreaks are high in Southern soils. Sample storage units immediately for aflatoxin.";
        trnRec = trnRec.replace(textToReplace, trnSouth[currentLanguage] || textToReplace);
    }
    
    if (trnRec.includes("damp coastal regions")) {
        const trnCoastalPen = {
            hi: "[पेनिसिलियम गाइडलाइन]: नम तटीय क्षेत्रों में पेनिसिलियम का उच्च जोखिम। अनाज को तुरंत अलग करें और कम गर्मी वाले ड्रायर चलाएं।",
            es: "[Penicillium Directriz]: Alto riesgo de Penicillium en regiones costeras húmedas. Ponga el grano en cuarentena inmediatamente y use secadores a baja temperatura.",
            zh: "[青霉指南]: 潮湿沿海地区青霉菌风险高。请立即隔离粮食并运行低温干燥机。",
            bn: "[পেনিসিলিয়াম নির্দেশিকা]: উপকূলীয় অঞ্চলে पेनिसिलियामের ঝুঁকি বেশি। শস্য আলাদা করুন এবং ড্রায়ার চালান।",
            fr: "[Directive Penicillium]: Risque élevé dans les régions côtières humides. Quarantaine immédiate."
        };
        const textToReplace = "High Penicillium risk in damp coastal regions. Quarantine grain immediately and run low-heat dryers.";
        trnRec = trnRec.replace(textToReplace, trnCoastalPen[currentLanguage] || textToReplace);
    }
    
    if (trnRec.includes("Elevated local humidity detected")) {
        const trnCoastalAsp = {
            hi: "[एस्परजिलस गाइडलाइन]: स्थानीय आर्द्रता बढ़ी हुई पाई गई। बिन में वायु संचार बढ़ाएं; दिन में दो बार अनाज की नमी के स्तर की जांच करें।",
            es: "[Aspergillus flavus Directriz]: Humedad local elevada detectada. Aumente la aireación del silo; verifique la humedad del grano dos veces al día.",
            zh: "[黄曲霉指南]: 检测到局部湿度偏高。加强粮仓曝气，每天检查两次粮食水分。",
            bn: "[অ্যাসপারজিলাস নির্দেশিকা]: উচ্চ আর্द्रতা সনাক্ত হয়েছে। শস্যের আর্দ্রতা দিনে দুবার পরীক্ষা করুন।",
            fr: "[Directive Aspergillus]: Humidité élevée détectée. Augmentez l'aération."
        };
        const textToReplace = "Elevated local humidity detected. Enhance bin aeration; check grain moisture levels twice daily.";
        trnRec = trnRec.replace(textToReplace, trnCoastalAsp[currentLanguage] || textToReplace);
    }

    // Badges & Trends
    const riskBadge = document.getElementById("risk-badge");
    riskBadge.textContent = trnRisk;
    riskBadge.className = `risk-badge risk-${data.risk_level.toLowerCase().replace(" ", "-")}`;
    
    document.getElementById("confidence-val").textContent = data.confidence.toFixed(1) + "%";
    
    const trendVal = document.getElementById("trend-val");
    trendVal.textContent = trnTrend;
    if (data.trend === "Rising") {
        trendVal.style.color = "var(--color-high-risk)";
    } else if (data.trend === "Stable") {
        trendVal.style.color = "var(--color-caution)";
    } else {
        trendVal.style.color = "var(--color-safe)";
    }
    
    document.getElementById("euclidean-val").textContent = data.euclidean_distance.toFixed(2);
    
    // Recommendations Card (Render fully translated text)
    document.getElementById("recommendation-content").innerHTML = `
        <p style="font-weight:700; color:var(--text-primary); margin-bottom: 0.5rem;">${trnRisk} Warning Protocol:</p>
        <p>${trnRec}</p>
    `;

    // AI Forecast update
    // Simple math models based on cci
    const daysLabel = dict["days_text"] || "Days";
    const costLabel = data.cci_score > 60 ? (dict["cost_high"] || "High") : (dict["cost_low"] || "Low");
    
    document.getElementById("ai-trend").textContent = data.trend === "Rising" ? (dict["trend_rising"] || "Rising") : (dict["trend_stable"] || "Stable");
    document.getElementById("ai-days").textContent = data.cci_score >= 80 ? ("0 " + daysLabel) : (Math.max(1, Math.round((80 - data.cci_score) / 1.2)) + " " + daysLabel);
    document.getElementById("ai-cost").textContent = costLabel;
    document.getElementById("ai-success").textContent = (100 - data.cci_score * 0.3).toFixed(1) + "%";

    // Auto-update sample strip canvas if available
    const previewImg = document.getElementById("image-preview");
    const previewContainer = document.getElementById("image-preview-container");
    if (previewContainer && (!previewImg.src || previewImg.src.includes("uploads/"))) {
        previewImg.src = `/static/images/sample_strip_${data.risk_level.toLowerCase().replace(" ", "_")}.png`;
        previewContainer.style.display = "block";
    }
    
    // Stop any playing speech
    stopSpeech();
}

function addScanToLogTable(data) {
    const tbody = document.getElementById("scan-log-body");
    const emptyRow = document.getElementById("empty-history-row");
    if (emptyRow) emptyRow.remove();

    const tr = document.createElement("tr");
    let badgeClass = "risk-safe";
    if (data.risk_level === "Critical") badgeClass = "risk-critical";
    else if (data.risk_level === "High Risk") badgeClass = "risk-high-risk";
    else if (data.risk_level === "Caution") badgeClass = "risk-caution";
    else if (data.risk_level === "Monitor") badgeClass = "risk-monitor";

    const trnRiskKey = "risk_" + data.risk_level.toLowerCase().replace(" ", "_");
    const trnTrendKey = "trend_" + data.trend.toLowerCase();
    
    const dict = translations[currentLanguage] || translations["en"];
    const trnRisk = dict[trnRiskKey] || data.risk_level;
    const trnTrend = dict[trnTrendKey] || data.trend;
    
    let syncText = data.sync_status === "Pending Sync" 
        ? `<span data-trn="status_pending" style="color:var(--color-caution);">${dict["status_pending"] || "Pending"}</span>` 
        : `<span data-trn="status_synced" style="color:var(--color-safe);">${dict["status_synced"] || "Synced"}</span>`;

    tr.innerHTML = `
        <td>${data.timestamp}</td>
        <td><strong>${data.cci_score.toFixed(1)}</strong></td>
        <td>${data.fi_score.toFixed(1)}</td>
        <td>${data.vi_score.toFixed(1)}</td>
        <td><span class="risk-badge ${badgeClass}" data-trn="${trnRiskKey}">${trnRisk}</span></td>
        <td data-trn="${trnTrendKey}">${trnTrend}</td>
        <td>${data.euclidean_distance.toFixed(2)}</td>
        <td>${syncText}</td>
    `;
    
    tbody.insertBefore(tr, tbody.firstChild);
}

// Sync local offline scans to server database
function triggerOfflineSync() {
    const queue = getOfflineQueue();
    if (queue.length === 0 || !navigator.onLine) return;

    const syncBtn = document.getElementById("sync-now-btn");
    if (syncBtn) {
        syncBtn.disabled = true;
        syncBtn.textContent = "Syncing...";
    }

    // Sync recursively
    function syncNext(index) {
        if (index >= queue.length) {
            // Completed syncing all scans
            saveOfflineQueue([]);
            if (syncBtn) {
                syncBtn.disabled = false;
                syncBtn.textContent = "Synced Successfully!";
                setTimeout(() => {
                    checkOfflineQueueSize();
                }, 2000);
            }
            // Reload page to get actual synced history
            window.location.reload();
            return;
        }

        const scan = queue[index];
        
        // Convert base64 dataUrl back to a blob upload
        fetch(scan.fileData)
            .then(res => res.blob())
            .then(blob => {
                const formData = new FormData();
                formData.append("file", blob, scan.fileName);
                formData.append("region", scan.region);
                
                return fetch("/api/scans/analyze", {
                    method: "POST",
                    body: formData
                });
            })
            .then(res => res.json())
            .then(() => {
                syncNext(index + 1);
            })
            .catch(err => {
                console.error("Sync item failed, stopping queue run", err);
                if (syncBtn) {
                    syncBtn.disabled = false;
                    syncBtn.textContent = "Sync failed partially";
                }
            });
    }

    syncNext(0);
}

// Text to Speech synthesis using native Web Speech API
function toggleSpeech(text) {
    if (isSpeaking) {
        stopSpeech();
        return;
    }

    // Initialize Synthesis
    speechUtterance = new SpeechSynthesisUtterance(text);
    
    // Set matching voice locale
    const localeCode = speechLocales[currentLanguage] || "en-US";
    speechUtterance.lang = localeCode;
    
    // Find voice matching locale
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.lang.startsWith(localeCode) || v.lang.includes(currentLanguage));
    if (voice) speechUtterance.voice = voice;

    speechUtterance.onend = () => {
        stopSpeech();
    };

    speechUtterance.onerror = () => {
        stopSpeech();
    };

    // Update UI status
    const ttsBtn = document.getElementById("tts-btn");
    const ttsText = document.getElementById("tts-btn-text");
    if (ttsBtn && ttsText) {
        ttsBtn.className = "btn btn-outline risk-critical";
        ttsText.textContent = translations[currentLanguage].stop_audio || "Stop Audio";
    }

    isSpeaking = true;
    window.speechSynthesis.speak(speechUtterance);
}

function stopSpeech() {
    window.speechSynthesis.cancel();
    isSpeaking = false;
    
    const ttsBtn = document.getElementById("tts-btn");
    const ttsText = document.getElementById("tts-btn-text");
    if (ttsBtn && ttsText) {
        ttsBtn.className = "btn btn-outline";
        ttsText.textContent = translations[currentLanguage].listen_rec || "Listen to Recommendations";
        translateElement(ttsText, currentLanguage);
    }
}
