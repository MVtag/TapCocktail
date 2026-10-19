/**
 * TapCocktail Lovelace Card
 * Version 1.4.0
 *
 * Example:
 * type: custom:tapcocktail-card
 * tap: 1
 *
 * Cocktail-dropdownen grupperes automatisk efter kategori
 * fra sensor.tapcocktail_library.
 */

class TapCocktailCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._lastRenderKey = null;
  }

  setConfig(config) {
    if (!config) throw new Error("Manglende kortkonfiguration");

    const tap = Number(config.tap ?? 1);
    if (!Number.isInteger(tap) || tap < 1) {
      throw new Error("'tap' skal være et positivt heltal");
    }

    this._config = {
      tap,
      name: config.name ?? `Hane ${tap}`,
      show_details: config.show_details !== false,
      show_cocktail_select: config.show_cocktail_select !== false,
      show_glass: config.show_glass !== false,
      show_bubbles: config.show_bubbles !== false,
      show_progress: config.show_progress !== false,
      show_controls: config.show_controls !== false,
      show_time_on_tap: config.show_time_on_tap !== false,
      show_shelf_life: config.show_shelf_life !== false,
      show_serving_tips: config.show_serving_tips !== false,
      show_recipe: config.show_recipe !== false,
      show_status: config.show_status !== false,
      show_tap_name: config.show_tap_name !== false,
      layout_preset: config.layout_preset ?? "custom",
      recipe_mode: config.recipe_mode ?? "button",
      recipe_amount: config.recipe_amount ?? "glass",
      recipe_large_text: config.recipe_large_text === true,
      compact: config.compact === true,
      preview_cocktail_id: config.preview_cocktail_id ?? null,
      ...config,
    };

    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const key = this._buildRenderKey();

    if (key !== this._lastRenderKey) {
      this._lastRenderKey = key;
      this._render();
    }
  }

  getCardSize() {
    return 5;
  }

  static getStubConfig() {
    return {
      tap: 1,
      name: "Hane 1",
      show_cocktail_select: true,
      show_details: true,
      show_glass: true,
      show_bubbles: true,
      show_progress: true,
      show_controls: true,
      show_time_on_tap: true,
      show_shelf_life: true,
      show_serving_tips: true,
      show_recipe: true,
      show_status: true,
      show_tap_name: true,
      recipe_mode: "button",
      recipe_amount: "glass",
      recipe_large_text: false,
      compact: false,
    };
  }

  static getConfigElement() {
    return document.createElement("tapcocktail-card-editor");
  }

  _entityIds() {
    const tap = this._config?.tap ?? 1;

    return {
      cocktail: `sensor.tapcocktail_hane_${tap}`,
      library: "sensor.tapcocktail_library",
      selection: `select.hane_${tap}_cocktail`,
      legacySelection: `input_select.tapcocktail_hane_${tap}`,
      carbonationSelect: `select.hane_${tap}_karbonering`,
      startButton: `button.hane_${tap}_start_karbonering`,
      stopButton: `button.hane_${tap}_stop_karbonering`,
      status: `sensor.hane_${tap}_status`,
      progress: `sensor.hane_${tap}_progress`,
      remaining: `sensor.hane_${tap}_remaining`,
      finished: `sensor.hane_${tap}_faerdig`,
      timeOnTap: `sensor.hane_${tap}_tid_pa_fad`,
    };
  }

  _state(entityId) {
    return this._hass?.states?.[entityId];
  }

  _buildRenderKey() {
    if (!this._hass || !this._config) return "";

    const entityKey = Object.values(this._entityIds())
      .map((entityId) => {
        const entity = this._state(entityId);
        return entity
          ? `${entityId}:${entity.state}:${entity.last_changed}`
          : `${entityId}:missing`;
      })
      .join("|");

    const cocktailEntity = this._state(this._entityIds().cocktail);
    const temperatureSensorId =
      cocktailEntity?.attributes?.temperatursensor ??
      cocktailEntity?.attributes?.temperature_sensor;
    const temperatureEntity = temperatureSensorId
      ? this._state(temperatureSensorId)
      : null;
    const temperatureKey = temperatureEntity
      ? `${temperatureSensorId}:${temperatureEntity.state}:${temperatureEntity.last_updated}`
      : `${temperatureSensorId ?? "none"}:missing`;

    // Shelf-life and "time on tap" labels change as time passes, even when
    // Home Assistant entity states themselves have not changed.
    return `${entityKey}|${temperatureKey}|minute:${Math.floor(Date.now() / 60000)}`;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _number(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  _displayIcon(icon, fallback = "🍹") {
    const value = String(icon ?? "").trim();
    if (!value) return fallback;
    return value;
  }

  _formatHours(value) {
    const totalHours = Math.max(0, Math.round(this._number(value, 0)));

    if (totalHours < 24) {
      return totalHours === 1 ? "1 time" : `${totalHours} timer`;
    }

    const days = Math.floor(totalHours / 24);
    const hours = totalHours % 24;
    const dayText = days === 1 ? "1 dag" : `${days} dage`;

    if (hours === 0) return dayText;

    const hourText = hours === 1 ? "1 time" : `${hours} timer`;
    return `${dayText} og ${hourText}`;
  }

  _formatTimestamp(entity) {
    if (!entity || ["unknown", "unavailable", "none", ""].includes(entity.state)) {
      return null;
    }

    const date = new Date(entity.state);
    if (Number.isNaN(date.getTime())) return null;

    const diffMs = date.getTime() - Date.now();
    const absMinutes = Math.round(Math.abs(diffMs) / 60000);

    if (absMinutes < 1) {
      return diffMs >= 0 ? "om få sekunder" : "Få sekunder";
    }

    if (absMinutes < 60) {
      if (diffMs >= 0) {
        return `om ${absMinutes} min.`;
      }

      return absMinutes === 1
        ? "1 minut"
        : `${absMinutes} minutter`;
    }

    const hours = Math.round(absMinutes / 60);

    if (hours < 24) {
      if (diffMs >= 0) {
        return `om ${hours} t.`;
      }

      return this._formatHours(hours);
    }

    const formatted = this._formatHours(hours);
    return diffMs >= 0 ? `om ${formatted}` : formatted;
  }

  _statusPresentation(status) {
    switch (status) {
      case "carbonating":
        return { label: "Karbonerer", icon: "mdi:weather-windy", css: "carbonating" };
      case "ready":
        return { label: "Klar", icon: "mdi:check-circle", css: "ready" };
      default:
        return { label: "Ikke startet", icon: "mdi:pause-circle", css: "idle" };
    }
  }

  _shelfLifePresentation(shelfLife, readyEntity) {
    const days = Number(shelfLife?.days);
    if (!Number.isFinite(days) || days <= 0 || !readyEntity) return null;
    if (["unknown", "unavailable", "none", ""].includes(readyEntity.state)) {
      return null;
    }

    const started = new Date(readyEntity.state);
    if (Number.isNaN(started.getTime())) return null;

    const dayMs = 24 * 60 * 60 * 1000;
    const elapsedDays = Math.max(0, (Date.now() - started.getTime()) / dayMs);
    const remaining = Math.ceil(days - elapsedDays);
    const usedRatio = elapsedDays / days;

    if (remaining < 0) {
      const overdue = Math.abs(remaining);
      return {
        css: "expired",
        label: `Holdbarhed overskredet med ${overdue} ${overdue === 1 ? "dag" : "dage"}`,
        detail: `Anbefalet holdbarhed: ${days} dage`,
      };
    }

    return {
      css: usedRatio >= 0.8 ? "warning" : "fresh",
      label:
        remaining === 0
          ? "Sidste anbefalede dag"
          : `${remaining} ${remaining === 1 ? "dag" : "dage"} tilbage`,
      detail: `Holdbarhed: ${days} dage`,
    };
  }


  _categoryLabel(category) {
    const raw = String(category || "Andre").trim();

    if (!raw) return "Andre";

    return raw
      .replaceAll("_", " ")
      .replaceAll("-", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  _buildCocktailOptionHtml(options, selected, libraryEntity) {
    if (!options.length) {
      return "<option>Ingen cocktails fundet</option>";
    }

    const library = libraryEntity?.attributes?.cocktails;

    if (!library || typeof library !== "object") {
      return options
        .map(
          (option) =>
            `<option value="${this._escape(option)}" ${
              option === selected ? "selected" : ""
            }>${this._escape(option)}</option>`
        )
        .join("");
    }

    const cocktails = Object.entries(library).map(([id, cocktail]) => {
      const data = cocktail && typeof cocktail === "object" ? cocktail : {};
      const name = String(data.navn ?? data.name ?? id);
      const icon = this._displayIcon(data.ikon ?? data.icon, "");

      return {
        id: String(id),
        name,
        displayName: icon ? `${icon} ${name}` : name,
        category: this._categoryLabel(data.kategori ?? data.category),
      };
    });

    const groups = new Map();

    options.forEach((option) => {
      const normalizedOption = String(option).trim();

      const match = cocktails.find((cocktail) => (
        normalizedOption === cocktail.displayName ||
        normalizedOption === cocktail.name ||
        normalizedOption === cocktail.id
      ));

      const category = match?.category ?? "Andre";

      if (!groups.has(category)) {
        groups.set(category, []);
      }

      groups.get(category).push(option);
    });

    return [...groups.entries()]
      .sort(([a], [b]) => a.localeCompare(b, "da"))
      .map(([category, categoryOptions]) => {
        const optionsHtml = categoryOptions
          .map(
            (option) =>
              `<option value="${this._escape(option)}" ${
                option === selected ? "selected" : ""
              }>${this._escape(option)}</option>`
          )
          .join("");

        return `<optgroup label="${this._escape(category)}">${optionsHtml}</optgroup>`;
      })
      .join("");
  }

  _recipeHtml({
    ingredients,
    method,
    garnish,
    notes,
    carbonationHours,
    amountMode = "glass",
    largeText = false,
  }) {
    const modes = {
      glass: { label: "Pr. glas", key: "glas" },
      two_liter: { label: "2 liter", key: "2_liter" },
      nine_liter: { label: "9 liter", key: "9_liter" },
    };

    const selected = modes[amountMode] ?? modes.glass;

    const recipeRows = ingredients
      .map((item) => {
        const name = String(item?.navn ?? item?.name ?? "").trim();
        const amount = String(
          item?.[selected.key] ??
          (selected.key === "2_liter"
            ? item?.two_liter
            : selected.key === "9_liter"
              ? item?.nine_liter
              : item?.glass) ??
          ""
        ).trim();

        return { name, amount };
      })
      .filter((item) => item.name && item.amount);

    const rows = recipeRows
      .map(
        (item) => `
          <tr>
            <td>${this._escape(item.name)}</td>
            <td>${this._escape(item.amount)}</td>
          </tr>
        `
      )
      .join("");

    const copyText = recipeRows
      .map((item) => `${item.name}: ${item.amount}`)
      .join("\n");

    return `
      <div class="recipe-sheet ${largeText ? "large-text" : ""}">
        <div class="recipe-header">
          <div>
            <div class="recipe-kicker">📖 Opskrift</div>
            <div class="recipe-title">Blandingsoversigt</div>
          </div>
          <button class="recipe-close" id="recipe-close" aria-label="Luk opskrift">
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>

        <div class="recipe-toolbar">
          <label class="recipe-amount-field">
            Mængde
            <select id="recipe-amount-select">
              <option value="glass" ${amountMode === "glass" ? "selected" : ""}>Pr. glas</option>
              <option value="two_liter" ${amountMode === "two_liter" ? "selected" : ""}>2 liter</option>
              <option value="nine_liter" ${amountMode === "nine_liter" ? "selected" : ""}>9 liter</option>
            </select>
          </label>

          <button class="recipe-tool-button" id="recipe-copy" data-copy="${this._escape(copyText)}">
            <ha-icon icon="mdi:content-copy"></ha-icon>
            Kopiér
          </button>

          <button class="recipe-tool-button" id="recipe-print">
            <ha-icon icon="mdi:printer"></ha-icon>
            Print
          </button>
        </div>

        ${
          rows
            ? `
              <div class="recipe-table-wrap">
                <table class="recipe-table">
                  <thead>
                    <tr>
                      <th>Ingrediens</th>
                      <th>${this._escape(selected.label)}</th>
                    </tr>
                  </thead>
                  <tbody>${rows}</tbody>
                </table>
              </div>
            `
            : `<div class="recipe-empty">Der er ingen gemte mængder til ${this._escape(selected.label.toLowerCase())}.</div>`
        }

        ${method ? `<div class="recipe-block"><div class="recipe-block-title">Fremgangsmåde</div><div class="recipe-block-text">${this._escape(method)}</div></div>` : ""}
        ${garnish ? `<div class="recipe-block"><div class="recipe-block-title">Pynt</div><div class="recipe-block-text">${this._escape(garnish)}</div></div>` : ""}
        ${carbonationHours !== null ? `<div class="recipe-block"><div class="recipe-block-title">Karboneringstid</div><div class="recipe-block-text">${this._escape(this._formatHours(carbonationHours))}</div></div>` : ""}
        ${notes ? `<div class="recipe-block"><div class="recipe-block-title">Noter</div><div class="recipe-block-text">${this._escape(notes)}</div></div>` : ""}
      </div>
    `;
  }

  _recipeDataFromAttributes(attrs) {
    return {
      ingredients: Array.isArray(attrs.ingredienser) ? attrs.ingredienser : [],
      method: attrs.fremgangsmaade ?? attrs.fremgangsmåde ?? attrs.method ?? "",
      garnish: attrs.pynt ?? attrs.garnish ?? "",
      notes: attrs.noter ?? attrs.notes ?? "",
      carbonationHours:
        attrs.karbonering?.tid_timer ??
        attrs.karboneringstid_timer ??
        attrs.carbonation_hours ??
        null,
    };
  }

  _bindRecipeSheet(sheet, attrs, dialog = null) {
    const rebuild = (amountMode) => {
      const html = this._recipeHtml({
        ...this._recipeDataFromAttributes(attrs),
        amountMode,
        largeText: this._config.recipe_large_text,
      });

      if (dialog) {
        dialog.innerHTML = html;
        this._bindRecipeSheet(dialog.querySelector(".recipe-sheet"), attrs, dialog);
      } else if (sheet) {
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html;
        const replacement = wrapper.firstElementChild;
        sheet.replaceWith(replacement);
        this._bindRecipeSheet(replacement, attrs, null);
      }
    };

    sheet?.querySelector("#recipe-amount-select")?.addEventListener("change", (event) => {
      rebuild(event.target.value);
    });

    sheet?.querySelector("#recipe-copy")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      const copyText = button?.dataset?.copy ?? "";

      try {
        await navigator.clipboard.writeText(copyText);
        button.innerHTML = '<ha-icon icon="mdi:check"></ha-icon>Kopieret';
      } catch (error) {
        console.error("TapCocktail: Kunne ikke kopiere opskrift", error);
      }
    });

    sheet?.querySelector("#recipe-print")?.addEventListener("click", () => {
      const printWindow = window.open("", "_blank", "width=820,height=900");
      if (!printWindow) return;

      printWindow.document.write(`
        <!doctype html>
        <html lang="da">
          <head>
            <meta charset="utf-8">
            <title>TapCocktail opskrift</title>
            <style>
              body { font-family: Arial, sans-serif; margin: 32px; color: #111; }
              button, select, label { display: none !important; }
              table { width: 100%; border-collapse: collapse; margin-top: 20px; }
              th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ccc; }
              .recipe-title { font-size: 28px; font-weight: 800; }
              .recipe-kicker, .recipe-block-title { font-weight: 700; margin-top: 18px; }
              .recipe-block { margin-top: 18px; }
              .recipe-block-text { white-space: pre-line; line-height: 1.5; }
            </style>
          </head>
          <body>${sheet?.outerHTML ?? ""}</body>
        </html>
      `);

      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
    });

    sheet?.querySelector("#recipe-close")?.addEventListener("click", () => {
      if (dialog) dialog.close();
      else sheet.remove();
    });
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;

    if (!this._hass) {
      this.shadowRoot.innerHTML = "<ha-card><div class='message'>Indlæser TapCocktail…</div></ha-card>";
      return;
    }

    const ids = this._entityIds();
    const cocktailEntity = this._state(ids.cocktail);

    if (!cocktailEntity) {
      this.shadowRoot.innerHTML = `<ha-card><div class="message">Kunne ikke finde <code>${this._escape(ids.cocktail)}</code></div></ha-card>`;
      return;
    }

    const libraryEntity = this._state(ids.library);
    const cocktailSelect =
      this._state(ids.selection) ??
      this._state(ids.legacySelection);
    const carbonationSelect = this._state(ids.carbonationSelect);
    const startButton = this._state(ids.startButton);
    const stopButton = this._state(ids.stopButton);
    const statusEntity = this._state(ids.status);
    const progressEntity = this._state(ids.progress);
    const remainingEntity = this._state(ids.remaining);
    const finishedEntity = this._state(ids.finished);
    const timeOnTapEntity = this._state(ids.timeOnTap);

    const liveAttrs = cocktailEntity.attributes ?? {};
    const libraryCocktails = libraryEntity?.attributes?.cocktails ?? {};
    const previewCocktail =
      this._config.preview_cocktail_id &&
      libraryCocktails &&
      typeof libraryCocktails === "object"
        ? libraryCocktails[this._config.preview_cocktail_id]
        : null;

    const attrs =
      previewCocktail && typeof previewCocktail === "object"
        ? previewCocktail
        : liveAttrs;

    const cocktailName =
      previewCocktail?.navn ??
      previewCocktail?.name ??
      cocktailEntity.state ??
      "Ingen cocktail";

    const compactCocktailName = attrs.navn || attrs.name || cocktailName;
    const titleLength = compactCocktailName.length;

    let cocktailFontSize = "25px";
    if (titleLength > 30) {
      cocktailFontSize = "17px";
    } else if (titleLength > 24) {
      cocktailFontSize = "19px";
    } else if (titleLength > 18) {
      cocktailFontSize = "22px";
    }

    const icon = this._displayIcon(attrs.ikon ?? attrs.icon);
    const requestedColor = attrs.farve || attrs.color;
    const color = /^#[0-9a-f]{6}$/i.test(requestedColor || "")
      ? requestedColor
      : "#7ed957";
    const abv = attrs.abv;
    const co2 = attrs.co2 ?? attrs.vol_co2;
    const temperature = attrs.temperatur ?? attrs.temperature;
    const temperatureSensorId =
      liveAttrs.temperatursensor ?? liveAttrs.temperature_sensor;
    const temperatureEntity = temperatureSensorId
      ? this._state(temperatureSensorId)
      : null;
    const measuredTemperature = (
      temperatureEntity &&
      !["unknown", "unavailable", "none", ""].includes(
        String(temperatureEntity.state).toLowerCase()
      ) &&
      Number.isFinite(Number(temperatureEntity.state))
    )
      ? Number(temperatureEntity.state).toLocaleString("da-DK", {
          maximumFractionDigits: 1,
        })
      : null;
    const temperatureText = temperature !== undefined
      ? `${measuredTemperature ? `${measuredTemperature} / ` : ""}${temperature}`
      : measuredTemperature;
    const glass = attrs.glas ?? attrs.glass;
    const shelfLife = attrs.holdbarhed ?? attrs.shelf_life;
    const servingTips =
      attrs.serveringstips ??
      attrs.servering_tip ??
      attrs.serving_tips ??
      "Ingen serveringstips endnu";

    const ingredients = Array.isArray(attrs.ingredienser)
      ? attrs.ingredienser
      : [];

    const method =
      attrs.fremgangsmaade ??
      attrs.fremgangsmåde ??
      attrs.method ??
      "";

    const garnish =
      attrs.pynt ??
      attrs.garnish ??
      "";

    const notes =
      attrs.noter ??
      attrs.notes ??
      "";

    const carbonationHours =
      attrs.karbonering?.tid_timer ??
      attrs.karboneringstid_timer ??
      attrs.carbonation_hours ??
      null;

    const hasRecipe =
      ingredients.length > 0 ||
      Boolean(method) ||
      Boolean(garnish) ||
      Boolean(notes) ||
      carbonationHours !== null;

    const status = statusEntity?.state ?? "idle";
    const statusUi = this._statusPresentation(status);
    const progress = Math.max(0, Math.min(100, this._number(progressEntity?.state)));
    const remaining = remainingEntity?.state ?? "Ikke startet";
    const finishedText = this._formatTimestamp(finishedEntity);
    const timeOnTapText = this._formatTimestamp(timeOnTapEntity);
    const shelfLifeUi = this._shelfLifePresentation(
      shelfLife,
      timeOnTapEntity
    );

    const cocktailOptions = cocktailSelect?.attributes?.options ?? [];

    // The tap sensor is the authoritative displayed cocktail. Using it here
    // keeps the dropdown in sync even while Home Assistant is updating the
    // select entity after a coordinator refresh.
    const selectedCocktail =
      cocktailEntity?.state ??
      cocktailSelect?.state ??
      "";

    const options = carbonationSelect?.attributes?.options ?? [];
    const selected = carbonationSelect?.state ?? "";
    const startDisabled = !startButton || startButton.state === "unavailable";
    const stopDisabled = !stopButton || stopButton.state === "unavailable";

    const co2Value = Math.max(2.0, Math.min(3.0, this._number(co2, 2.0)));
    const bubbleLevel = Math.max(0, Math.min(1, (co2Value - 2.0) / 1.0));
    const bubbleCount = Math.round(18 + bubbleLevel * 26);
    const bubbleScale = (1.05 + bubbleLevel * 0.40).toFixed(2);
    const bubbleBaseDuration = 8.0 - bubbleLevel * 3.2;

    const bubbles = Array.from({ length: bubbleCount }, (_, index) => {
      const left = (index * 17 + 7) % 100;
      const size = 10 + ((index * 5) % 18);
      const speed = Math.max(
        4.0,
        bubbleBaseDuration + (((index * 7) % 9) - 4) * 0.24
      ).toFixed(2);
      const delay = -((index * 1.26) % 10).toFixed(2);

      return `<span class="bubble" style="left:${left}%;--size:${size}px;--speed:${speed}s;--delay:${delay}s"></span>`;
    }).join("");

    const cocktailOptionHtml = this._buildCocktailOptionHtml(
      cocktailOptions,
      selectedCocktail,
      libraryEntity
    );

    const optionHtml = options.length
      ? options.map((option) => `<option value="${this._escape(option)}" ${option === selected ? "selected" : ""}>${this._escape(option)}</option>`).join("")
      : "<option>Ingen valgmuligheder</option>";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        ha-card {
          --cocktail-color:${this._escape(color)};
          position:relative;
          overflow:hidden;
          border-radius:28px;
          padding:22px;
          color:var(--primary-text-color);
          background:
            radial-gradient(circle at 88% 8%, color-mix(in srgb, var(--cocktail-color) 34%, transparent), transparent 38%),
            linear-gradient(145deg, color-mix(in srgb, var(--card-background-color) 86%, var(--cocktail-color)), var(--card-background-color));
        }
        .content { position:relative; z-index:1; }
        .bubbles {
          position:absolute;
          inset:0;
          overflow:hidden;
          pointer-events:none;
          transform:scale(${bubbleScale});
          transform-origin:center;
        }
        .bubble {
          position:absolute;
          bottom:-24px;
          width:var(--size);
          height:var(--size);
          border:1.5px solid rgba(15,15,20,0.55);
          background:
            radial-gradient(circle at 35% 30%,
              rgba(255,255,255,0.98) 0%,
              rgba(255,255,255,0.75) 45%,
              rgba(255,255,255,0.32) 100%);
          box-shadow:
            0 0 0 1px rgba(0,0,0,0.45),
            0 0 9px rgba(255,255,255,0.7);
          border-radius:50%;
          animation:rise var(--speed) linear infinite;
          animation-delay:var(--delay);
        }
        .bubble::after {
          content:"";
          position:absolute;
          top:16%;
          left:20%;
          width:26%;
          height:26%;
          border-radius:50%;
          background:rgba(255,255,255,0.98);
          box-shadow:0 0 5px rgba(255,255,255,0.95);
        }
        @media (prefers-reduced-motion: reduce) {
          .bubble {
            animation:none;
            opacity:.8;
            bottom:20%;
          }
        }

        @keyframes rise {
          from {
            bottom:-32px;
            transform:scale(.8);
            opacity:0;
          }
          15% { opacity:.7; }
          85% { opacity:.7; }
          to {
            bottom:calc(100% + 32px);
            transform:scale(1.15);
            opacity:0;
          }
        }
        .top { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:14px; }
        .cocktail-icon {
          display:grid;
          place-items:center;
          width:68px;
          height:68px;
          border-radius:22px;
          font-size:42px;
          background:color-mix(in srgb, var(--cocktail-color) 24%, transparent);
          border:1px solid color-mix(in srgb, var(--cocktail-color) 45%, transparent);
        }
        .title { min-width:0; }
        .tap-name { font-size:13px; opacity:.7; margin-bottom:3px; }
        .cocktail-name {
          overflow:hidden;
          display:-webkit-box;
          -webkit-box-orient:vertical;
          -webkit-line-clamp:2;
          line-clamp:2;
          white-space:normal;
          word-break:break-word;
          font-size:${cocktailFontSize};
          font-weight:700;
          line-height:1.08;
          max-width:100%;
        }
        .status { display:inline-flex; align-items:center; gap:6px; padding:7px 10px; border-radius:999px; font-size:12px; font-weight:700; white-space:nowrap; }
        .status.idle { background:color-mix(in srgb, var(--secondary-text-color) 15%, transparent); }
        .status.carbonating { background:color-mix(in srgb, #f2b544 26%, transparent); }
        .status.ready { background:color-mix(in srgb, #55c979 26%, transparent); }
        .cocktail-picker { margin-top:16px; }
        .cocktail-picker label {
          display:block;
          margin:0 0 7px 2px;
          font-size:13px;
          font-weight:700;
          opacity:.78;
        }
        .details { display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }
        .detail { padding:7px 10px; border-radius:12px; font-size:13px; background:color-mix(in srgb, var(--primary-text-color) 7%, transparent); }
        .progress-section { margin-top:20px; }
        .progress-header { display:flex; justify-content:space-between; align-items:baseline; gap:12px; margin-bottom:8px; }
        .progress-label,.progress-value { font-size:14px; font-weight:700; }
        .progress-track { height:12px; overflow:hidden; border-radius:999px; background:color-mix(in srgb, var(--primary-text-color) 12%, transparent); }
        .progress-bar { height:100%; width:${progress}%; border-radius:inherit; background:linear-gradient(90deg, color-mix(in srgb, var(--cocktail-color) 78%, white), var(--cocktail-color)); transition:width 300ms ease; }
        .time-row { display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px 16px; margin-top:10px; font-size:13px; opacity:.84; }

        .ready-section {
          margin-top:8px;
          padding:16px;
          border-radius:18px;
          background:
            linear-gradient(
              135deg,
              color-mix(in srgb, var(--cocktail-color) 28%, white),
              color-mix(in srgb, var(--card-background-color) 88%, white)
            );
          border:1px solid color-mix(in srgb, var(--cocktail-color) 38%, transparent);
        }
        .ready-badge {
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding:8px 12px;
          border-radius:999px;
          font-size:13px;
          font-weight:800;
          color:var(--primary-text-color);
          background:color-mix(in srgb, var(--cocktail-color) 18%, white);
        }
        .ready-badge ha-icon {
          --mdc-icon-size:18px;
          color:color-mix(in srgb, var(--cocktail-color) 68%, black);
        }
        .ready-time {
          margin-top:12px;
          font-size:24px;
          font-weight:800;
          line-height:1.15;
          text-align:center;
          color:var(--primary-text-color);
        }
        .ready-subtext {
          margin-top:6px;
          font-size:13px;
          text-align:center;
          color:var(--secondary-text-color);
        }
        .shelf-life {
          margin-top:12px;
          padding:10px 12px;
          border-radius:12px;
          text-align:center;
          font-size:13px;
          font-weight:800;
        }
        .shelf-life.fresh {
          color:#155724;
          background:#d4edda;
        }
        .shelf-life.warning {
          color:#7a4b00;
          background:#fff3cd;
        }
        .shelf-life.expired {
          color:#842029;
          background:#f8d7da;
        }
        .shelf-life-detail {
          margin-top:3px;
          font-size:11px;
          font-weight:600;
          opacity:.78;
        }
        .controls { display:grid; grid-template-columns:minmax(0,1fr) auto auto; gap:10px; margin-top:20px; }
        select,button { min-height:42px; border:0; border-radius:13px; font:inherit; }
        select { width:100%; padding:0 12px; color:var(--primary-text-color); background:color-mix(in srgb, var(--primary-text-color) 9%, transparent); }
        button { display:inline-flex; align-items:center; justify-content:center; gap:7px; padding:0 15px; cursor:pointer; color:var(--text-primary-color,white); font-weight:700; background:var(--cocktail-color); }
        button.stop { color:var(--primary-text-color); background:color-mix(in srgb, var(--primary-text-color) 12%, transparent); }
        button:disabled { cursor:not-allowed; opacity:.4; }
        .message { padding:22px; }

        .serving-tips {
          margin-top:20px;
          padding:18px;
          border-radius:18px;
          text-align:center;
          background:
            linear-gradient(
              135deg,
              color-mix(in srgb, var(--cocktail-color) 22%, transparent),
              color-mix(in srgb, var(--card-background-color) 88%, white)
            );
          border:1px solid color-mix(in srgb, var(--cocktail-color) 35%, transparent);
        }

        .serving-tips-title {
          display:flex;
          align-items:center;
          justify-content:center;
          gap:8px;
          margin-bottom:10px;
          font-size:18px;
          font-weight:800;
        }

        .serving-tips-text {
          font-size:15px;
          line-height:1.5;
          white-space:pre-line;
          color:var(--primary-text-color);
        }

        .recipe-action {
          margin-top:16px;
        }

        .recipe-button {
          width:100%;
          min-height:44px;
          border-radius:14px;
          background:color-mix(in srgb, var(--cocktail-color) 24%, var(--card-background-color));
          color:var(--primary-text-color);
          border:1px solid color-mix(in srgb, var(--cocktail-color) 42%, transparent);
          font-weight:800;
        }

        .recipe-dialog {
          width:min(760px, calc(100vw - 32px));
          max-height:min(82vh, 820px);
          padding:0;
          overflow:auto;
          border:0;
          border-radius:24px;
          background:var(--card-background-color);
          color:var(--primary-text-color);
          box-shadow:0 24px 80px rgba(0,0,0,.35);
        }

        .recipe-dialog::backdrop {
          background:rgba(0,0,0,.58);
          backdrop-filter:blur(4px);
        }

        .recipe-sheet {
          padding:22px;
        }

        .recipe-header {
          display:flex;
          align-items:flex-start;
          justify-content:space-between;
          gap:16px;
          margin-bottom:18px;
        }

        .recipe-kicker {
          font-size:13px;
          font-weight:800;
          opacity:.7;
        }

        .recipe-title {
          margin-top:3px;
          font-size:24px;
          font-weight:900;
        }

        .recipe-close {
          width:42px;
          min-width:42px;
          padding:0;
          color:var(--primary-text-color);
          background:color-mix(in srgb, var(--primary-text-color) 10%, transparent);
        }

        .recipe-table-wrap {
          overflow:auto;
          border-radius:16px;
          border:1px solid var(--divider-color);
        }

        .recipe-table {
          width:100%;
          border-collapse:collapse;
          min-width:560px;
        }

        .recipe-table th,
        .recipe-table td {
          padding:12px 14px;
          text-align:left;
          border-bottom:1px solid var(--divider-color);
        }

        .recipe-table th {
          font-size:12px;
          text-transform:uppercase;
          letter-spacing:.04em;
          opacity:.7;
          background:color-mix(in srgb, var(--cocktail-color) 12%, transparent);
        }

        .recipe-table td:first-child {
          font-weight:800;
        }

        .recipe-block {
          margin-top:16px;
          padding:16px;
          border-radius:16px;
          background:color-mix(in srgb, var(--primary-text-color) 6%, transparent);
        }

        .recipe-block-title {
          margin-bottom:6px;
          font-size:13px;
          font-weight:900;
          text-transform:uppercase;
          letter-spacing:.03em;
          opacity:.7;
        }

        .recipe-block-text {
          white-space:pre-line;
          line-height:1.5;
        }

        .recipe-toolbar {
          display:grid;
          grid-template-columns:minmax(0,1fr) auto auto;
          gap:10px;
          margin-bottom:16px;
        }

        .recipe-amount-field {
          display:grid;
          gap:6px;
          font-size:13px;
          font-weight:700;
        }

        .recipe-tool-button {
          align-self:end;
          min-height:42px;
          color:var(--primary-text-color);
          background:color-mix(in srgb, var(--primary-text-color) 10%, transparent);
        }

        .recipe-empty {
          padding:18px;
          border-radius:16px;
          text-align:center;
          color:var(--secondary-text-color);
          background:color-mix(in srgb, var(--primary-text-color) 6%, transparent);
        }

        .recipe-sheet.large-text {
          font-size:18px;
        }

        .recipe-sheet.large-text .recipe-title {
          font-size:30px;
        }

        .recipe-sheet.large-text .recipe-table th,
        .recipe-sheet.large-text .recipe-table td {
          padding:16px;
          font-size:18px;
        }

        @media (max-width:600px) {
          .recipe-toolbar {
            grid-template-columns:1fr 1fr;
          }

          .recipe-amount-field {
            grid-column:1/-1;
          }

          .recipe-table {
            min-width:0;
          }
        }

        ha-card.compact {
          min-height:300px;
          box-sizing:border-box;
          padding:20px;
          border-radius:30px;
          color:#111111;
          background:
            linear-gradient(
              135deg,
              var(--cocktail-color),
              rgba(255,255,255,0.25)
            );
        }

        .compact-content {
          position:relative;
          z-index:1;
          min-height:260px;
          display:flex;
          flex-direction:column;
          align-items:center;
          justify-content:center;
          text-align:center;
        }

        .compact-emoji {
          font-size:72px;
          line-height:1;
          margin-top:4px;
        }

        .compact-name {
          max-width:90%;
          margin-top:10px;
          color:#111111;
          font-size:${cocktailFontSize};
          font-weight:800;
          line-height:1.08;
          text-transform:uppercase;
          overflow-wrap:anywhere;
        }

        .compact-info {
          display:flex;
          flex-wrap:wrap;
          justify-content:center;
          align-items:center;
          gap:8px 14px;
          margin-top:22px;
          color:#111111;
          font-size:18px;
          line-height:1.4;
        }

        .compact-glass {
          margin-top:12px;
          color:#111111;
          font-size:20px;
          font-weight:600;
          opacity:.95;
        }
        ha-card.compact .cocktail-icon {
          width:54px;
          height:54px;
          border-radius:18px;
          font-size:34px;
        }
        ha-card.compact .cocktail-name {
          font-size:min(${cocktailFontSize}, 21px);
        }
        ha-card.compact .cocktail-picker,
        ha-card.compact .details,
        ha-card.compact .progress-section,
        ha-card.compact .controls {
          margin-top:12px;
        }
        ha-card.compact .detail {
          padding:6px 9px;
          font-size:12px;
        }
        ha-card.compact select,
        ha-card.compact button {
          min-height:38px;
        }

        @media (max-width:480px) {
          .top { grid-template-columns:auto 1fr; }
          .status { grid-column:1/-1; justify-self:start; }
          .controls { grid-template-columns:1fr 1fr; }
          .controls select { grid-column:1/-1; }
        }
      </style>

      <ha-card class="${this._config.compact ? "compact" : ""}">
        ${this._config.show_bubbles ? `<div class="bubbles" aria-hidden="true">${bubbles}</div>` : ""}

        ${this._config.compact ? `
          <div class="compact-content">
            <div class="compact-emoji">${this._escape(icon)}</div>

            <div class="compact-name">
              ${this._escape(compactCocktailName)}
            </div>

            ${this._config.show_details ? `
              <div class="compact-info">
                ${abv !== undefined ? `<span>🥃 ${this._escape(abv)} %</span>` : ""}
                ${co2 !== undefined ? `<span>💨 ${this._escape(co2)} vol</span>` : ""}
                ${temperatureText !== null ? `<span>🌡️ ${this._escape(temperatureText)} °C</span>` : ""}
              </div>` : ""}

            ${this._config.show_glass && glass
              ? `<div class="compact-glass">🍸 ${this._escape(glass)}</div>`
              : ""}
          </div>
        ` : `
          <div class="content">
            <div class="top">
              <div class="cocktail-icon">${this._escape(icon)}</div>
              <div class="title">
                ${this._config.show_tap_name ? `<div class="tap-name">${this._escape(this._config.name)}</div>` : ""}
                <div class="cocktail-name">${this._escape(cocktailName)}</div>
              </div>
              ${this._config.show_status ? `
                <div class="status ${statusUi.css}">
                  <ha-icon icon="${statusUi.icon}"></ha-icon>
                  ${this._escape(statusUi.label)}
                </div>` : ""}
            </div>

            ${this._config.show_cocktail_select ? `
              <div class="cocktail-picker">
                <label for="cocktail-select">Vælg cocktail</label>
                <select id="cocktail-select" ${cocktailSelect ? "" : "disabled"}>
                  ${cocktailOptionHtml}
                </select>
              </div>` : ""}

            ${this._config.show_details ? `
              <div class="details">
                ${abv !== undefined ? `<div class="detail">🥃 ${this._escape(abv)} % ABV</div>` : ""}
                ${co2 !== undefined ? `<div class="detail">💨 ${this._escape(co2)} vol CO₂</div>` : ""}
                ${temperatureText !== null ? `<div class="detail">🌡️ ${this._escape(temperatureText)} °C</div>` : ""}
                ${this._config.show_glass && glass ? `<div class="detail">🍸 ${this._escape(glass)}</div>` : ""}
              </div>` : ""}

            ${this._config.show_progress ? `
              <div class="progress-section">
                ${status === "ready"
                  ? `
                    <div class="ready-section">
                      <div class="ready-badge">
                        <ha-icon icon="mdi:check-circle"></ha-icon>
                        <span>Klar til servering</span>
                      </div>
                      <div class="ready-time">
                        ${this._config.show_time_on_tap && timeOnTapText
                          ? this._escape(timeOnTapText)
                          : "Klar nu"}
                      </div>
                      <div class="ready-subtext">Tid på fad</div>
                      ${this._config.show_shelf_life && shelfLifeUi
                        ? `<div class="shelf-life ${shelfLifeUi.css}">
                            <div>${this._escape(shelfLifeUi.label)}</div>
                            <div class="shelf-life-detail">${this._escape(shelfLifeUi.detail)}</div>
                          </div>`
                        : ""}
                    </div>
                  `
                  : `
                    <div class="progress-header">
                      <span class="progress-label">Karbonering</span>
                      <span class="progress-value">${progress.toFixed(1)} %</span>
                    </div>
                    <div class="progress-track"><div class="progress-bar"></div></div>
                    <div class="time-row">
                      <span>⏱️ ${this._escape(remaining)}</span>
                      ${status === "carbonating" && finishedText ? `<span>Færdig ${this._escape(finishedText)}</span>` : ""}
                    </div>
                  `}
              </div>` : ""}

            ${this._config.show_controls ? `
              <div class="controls">
                <select id="carbonation-select" ${carbonationSelect ? "" : "disabled"}>${optionHtml}</select>
                <button id="start-button" ${startDisabled ? "disabled" : ""}>
                  <ha-icon icon="mdi:play"></ha-icon>Start
                </button>
                <button id="stop-button" class="stop" ${stopDisabled ? "disabled" : ""}>
                  <ha-icon icon="mdi:stop"></ha-icon>Stop
                </button>
              </div>` : ""}

            ${this._config.show_serving_tips ? `
              <div class="serving-tips">
                <div class="serving-tips-title">
                  <span>🍹</span>
                  <span>Serveringstips</span>
                </div>
                <div class="serving-tips-text">
                  ${this._escape(servingTips)}
                </div>
              </div>` : ""}

            ${
              this._config.show_recipe && hasRecipe
                ? this._config.recipe_mode === "inline"
                  ? this._recipeHtml({
                      ingredients,
                      method,
                      garnish,
                      notes,
                      carbonationHours,
                      amountMode: this._config.recipe_amount,
                      largeText: this._config.recipe_large_text,
                    })
                  : `
                    <div class="recipe-action">
                      <button class="recipe-button" id="recipe-open">
                        <ha-icon icon="mdi:book-open-page-variant"></ha-icon>
                        Se opskrift
                      </button>
                    </div>
                  `
                : ""
            }

            <dialog class="recipe-dialog" id="recipe-dialog"></dialog>
          </div>
        `}
      </ha-card>
    `;

    const cocktailDropdown =
      this.shadowRoot?.querySelector("#cocktail-select");

    if (cocktailDropdown && selectedCocktail) {
      cocktailDropdown.value = selectedCocktail;
    }

    this._attachEventListeners(ids);

    if (
      this._config.show_recipe &&
      this._config.recipe_mode === "inline" &&
      hasRecipe
    ) {
      this._bindRecipeSheet(
        this.shadowRoot?.querySelector(".recipe-sheet"),
        attrs,
        null
      );
    }
  }

  _attachEventListeners(ids) {
    this.shadowRoot?.querySelector("#cocktail-select")?.addEventListener("change", (event) => {
      const entityId = this._state(ids.selection)
        ? ids.selection
        : ids.legacySelection;
      const domain = entityId.split(".", 1)[0];

      this._hass.callService(domain, "select_option", {
        entity_id: entityId,
        option: event.target.value,
      });
    });

    this.shadowRoot?.querySelector("#carbonation-select")?.addEventListener("change", (event) => {
      this._hass.callService("select", "select_option", {
        entity_id: ids.carbonationSelect,
        option: event.target.value,
      });
    });

    this.shadowRoot?.querySelector("#start-button")?.addEventListener("click", () => {
      this._hass.callService("button", "press", { entity_id: ids.startButton });
    });

    this.shadowRoot?.querySelector("#stop-button")?.addEventListener("click", () => {
      this._hass.callService("button", "press", { entity_id: ids.stopButton });
    });

    this.shadowRoot?.querySelector("#recipe-open")?.addEventListener("click", () => {
      const cocktailEntity = this._state(ids.cocktail);
      const libraryEntity = this._state(ids.library);
      const previewCocktail =
        this._config.preview_cocktail_id &&
        libraryEntity?.attributes?.cocktails?.[this._config.preview_cocktail_id];

      const attrs =
        previewCocktail && typeof previewCocktail === "object"
          ? previewCocktail
          : cocktailEntity?.attributes ?? {};

      const dialog = this.shadowRoot?.querySelector("#recipe-dialog");
      if (!dialog) return;

      dialog.innerHTML = this._recipeHtml({
        ...this._recipeDataFromAttributes(attrs),
        amountMode: this._config.recipe_amount,
        largeText: this._config.recipe_large_text,
      });

      this._bindRecipeSheet(
        dialog.querySelector(".recipe-sheet"),
        attrs,
        dialog
      );

      dialog.addEventListener(
        "click",
        (event) => {
          if (event.target === dialog) dialog.close();
        },
        { once: true }
      );

      dialog.showModal();
    });

    this.shadowRoot?.querySelector("#recipe-close")?.addEventListener("click", () => {
      this.shadowRoot.querySelector(".recipe-sheet")?.remove();
    });
  }
}


class TapCocktailCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = {};
    this._previewCocktailId = "";
  }

  set hass(hass) {
    this._hass = hass;

    // Home Assistant opdaterer hass meget ofte. Hvis hele editoren
    // renderes ved hver opdatering, lukker åbne dropdown-menuer.
    if (!this._editorRendered) {
      this._editorRendered = true;
      this._render();
      return;
    }

    // Opdater kun live-forhåndsvisningen uden at genopbygge editoren.
    const previewCard = this._value("preview-card");
    if (previewCard) {
      previewCard.hass = hass;
    }
  }

  setConfig(config) {
    this._config = {
      tap: 1,
      name: "Hane 1",
      show_cocktail_select: true,
      show_details: true,
      show_glass: true,
      show_bubbles: true,
      show_progress: true,
      show_controls: true,
      show_time_on_tap: true,
      show_shelf_life: true,
      show_serving_tips: true,
      show_recipe: true,
      show_status: true,
      show_tap_name: true,
      layout_preset: "custom",
      recipe_mode: "button",
      recipe_amount: "glass",
      recipe_large_text: false,
      compact: false,
      ...config,
    };
    this._editorRendered = true;
    this._render();
  }

  _value(id) {
    return this.shadowRoot?.getElementById(id);
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _displayIcon(icon, fallback = "🍹") {
    const value = String(icon ?? "").trim();
    if (!value) return fallback;
    return value;
  }

  _libraryCocktails() {
    const library = this._hass?.states?.["sensor.tapcocktail_library"];
    const cocktails = library?.attributes?.cocktails;

    return cocktails && typeof cocktails === "object"
      ? cocktails
      : {};
  }

  _previewOptions() {
    const cocktails = this._libraryCocktails();

    return Object.entries(cocktails)
      .sort(([, a], [, b]) =>
        String(a?.navn ?? "").localeCompare(String(b?.navn ?? ""), "da")
      )
      .map(([id, cocktail]) => {
        const icon = this._displayIcon(cocktail?.ikon);
        const name = cocktail?.navn ?? id;
        const selected = id === this._previewCocktailId ? "selected" : "";

        return `<option value="${this._escape(id)}" ${selected}>${this._escape(
          `${icon} ${name}`
        )}</option>`;
      })
      .join("");
  }

  _emitConfig(changes) {
    const config = {
      ...this._config,
      ...changes,
    };

    this._config = config;

    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;

    const tap = Number(this._config.tap ?? 1);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display:block;
          padding:4px 0;
        }

        .editor {
          display:grid;
          gap:16px;
        }

        .section {
          display:grid;
          gap:10px;
          padding:14px;
          border:1px solid var(--divider-color);
          border-radius:14px;
          background:var(--card-background-color);
        }

        .section-title {
          font-size:14px;
          font-weight:700;
        }

        label.field {
          display:grid;
          gap:6px;
          font-size:13px;
        }

        select,
        input[type="text"] {
          box-sizing:border-box;
          width:100%;
          min-height:42px;
          padding:0 12px;
          color:var(--primary-text-color);
          background:var(--secondary-background-color);
          border:1px solid var(--divider-color);
          border-radius:10px;
          font:inherit;
        }

        label.toggle {
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:16px;
          min-height:34px;
          font-size:14px;
        }

        input[type="checkbox"] {
          width:20px;
          height:20px;
          accent-color:var(--primary-color);
        }

        .hint {
          color:var(--secondary-text-color);
          font-size:12px;
          line-height:1.4;
        }

        .preview-wrap {
          display:grid;
          gap:12px;
        }

        .preview-frame {
          padding:10px;
          border-radius:18px;
          background:var(--secondary-background-color);
          border:1px solid var(--divider-color);
        }

        .preview-frame tapcocktail-card {
          display:block;
        }
      </style>

      <div class="editor">
        <div class="section">
          <div class="section-title">Grundindstillinger</div>

          <label class="field">
            Hane
            <select id="tap">
              ${Array.from({ length: 8 }, (_, index) => {
                const tapNumber = index + 1;
                return `<option value="${tapNumber}" ${
                  tap === tapNumber ? "selected" : ""
                }>Hane ${tapNumber}</option>`;
              }).join("")}
            </select>
          </label>

          <label class="field">
            Kortets navn
            <input
              id="name"
              type="text"
              value="${String(this._config.name ?? `Hane ${tap}`)
                .replaceAll("&", "&amp;")
                .replaceAll('"', "&quot;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")}"
            />
          </label>
        </div>

        <div class="section">
          <div class="section-title">Kort-layout</div>
          <label class="field">
            Forudindstilling
            <select id="layout_preset">
              <option value="custom" ${this._config.layout_preset === "custom" ? "selected" : ""}>
                Brugerdefineret
              </option>
              <option value="full" ${this._config.layout_preset === "full" ? "selected" : ""}>
                Standard – alt vist
              </option>
              <option value="serving" ${this._config.layout_preset === "serving" ? "selected" : ""}>
                Servering
              </option>
              <option value="carbonation" ${this._config.layout_preset === "carbonation" ? "selected" : ""}>
                Karbonering
              </option>
              <option value="compact" ${this._config.layout_preset === "compact" ? "selected" : ""}>
                Kompakt
              </option>
              <option value="minimal" ${this._config.layout_preset === "minimal" ? "selected" : ""}>
                Minimal
              </option>
            </select>
          </label>
          <div class="hint">Vælg et layout og tilpas bagefter de enkelte visningsvalg.</div>
        </div>

        <div class="section">
          <div class="section-title">Visning</div>

          ${this._toggle("show_tap_name", "Vis hanens navn")}
          ${this._toggle("show_status", "Vis status")}
          ${this._toggle("show_cocktail_select", "Vis cocktailvælger")}
          ${this._toggle("show_details", "Vis ABV, CO₂ og temperatur")}
          ${this._toggle("show_glass", "Vis glastype")}
          ${this._toggle("show_bubbles", "Vis CO₂-bobler")}
          ${this._toggle("show_progress", "Vis karboneringsstatus")}
          ${this._toggle("show_controls", "Vis start, stop og tidsvalg")}
          ${this._toggle("show_time_on_tap", "Vis tid på fad")}
          ${this._toggle("show_shelf_life", "Vis holdbarhed på fad")}
          ${this._toggle("show_serving_tips", "Vis serveringstips")}
          ${this._toggle("show_recipe", "Vis opskrift")}

          <label class="field">
            Opskriftsvisning
            <select id="recipe_mode">
              <option value="button" ${this._config.recipe_mode === "button" ? "selected" : ""}>
                Knap: Se opskrift
              </option>
              <option value="inline" ${this._config.recipe_mode === "inline" ? "selected" : ""}>
                Vis direkte på kortet
              </option>
            </select>
          </label>

          <label class="field">
            Standardmængde i opskrift
            <select id="recipe_amount">
              <option value="glass" ${this._config.recipe_amount === "glass" ? "selected" : ""}>Pr. glas</option>
              <option value="two_liter" ${this._config.recipe_amount === "two_liter" ? "selected" : ""}>2 liter</option>
              <option value="nine_liter" ${this._config.recipe_amount === "nine_liter" ? "selected" : ""}>9 liter</option>
            </select>
          </label>

          ${this._toggle("recipe_large_text", "Stor tekst i opskrift")}
          ${this._toggle("compact", "Kompakt visning")}
        </div>

        <div class="section preview-wrap">
          <div class="section-title">Live-forhåndsvisning</div>

          <label class="field">
            Cocktail i forhåndsvisning
            <select id="preview-cocktail">
              <option value="">Brug cocktailen på den valgte hane</option>
              ${this._previewOptions()}
            </select>
          </label>

          <div class="preview-frame">
            <tapcocktail-card id="preview-card"></tapcocktail-card>
          </div>
        </div>

        <div class="hint">
          Ændringer vises straks i forhåndsvisningen.
        </div>
      </div>
    `;

    const previewCard = this._value("preview-card");

    if (previewCard && this._hass) {
      previewCard.setConfig({
        ...this._config,
        preview_cocktail_id: this._previewCocktailId || null,
      });
      previewCard.hass = this._hass;
    }

    this._bindEvents();
  }

  _toggle(key, label) {
    return `
      <label class="toggle">
        <span>${label}</span>
        <input
          id="${key}"
          type="checkbox"
          ${this._config[key] !== false && (key !== "compact" || this._config[key] === true) ? "checked" : ""}
        />
      </label>
    `;
  }

  _bindEvents() {
    this._value("preview-cocktail")?.addEventListener("change", (event) => {
      this._previewCocktailId = event.target.value;
      this._render();
    });

    this._value("tap")?.addEventListener("change", (event) => {
      const tap = Number(event.target.value);
      const oldDefaultName = `Hane ${this._config.tap ?? 1}`;
      const newDefaultName = `Hane ${tap}`;
      const currentName = this._config.name ?? oldDefaultName;

      this._emitConfig({
        tap,
        name: currentName === oldDefaultName ? newDefaultName : currentName,
      });

      this._render();
    });

    this._value("name")?.addEventListener("input", (event) => {
      this._emitConfig({ name: event.target.value });
    });

    this._value("layout_preset")?.addEventListener("change", (event) => {
      const presets = {
        full: {compact:false,show_tap_name:true,show_status:true,show_cocktail_select:true,show_details:true,show_glass:true,show_bubbles:true,show_progress:true,show_controls:true,show_time_on_tap:true,show_shelf_life:true,show_serving_tips:true,show_recipe:true},
        serving: {compact:false,show_tap_name:true,show_status:true,show_cocktail_select:true,show_details:true,show_glass:true,show_bubbles:true,show_progress:false,show_controls:false,show_time_on_tap:false,show_serving_tips:true,show_recipe:true},
        carbonation: {compact:false,show_tap_name:true,show_status:true,show_cocktail_select:true,show_details:true,show_glass:true,show_bubbles:true,show_progress:true,show_controls:true,show_time_on_tap:true,show_serving_tips:false,show_recipe:false},
        compact: {compact:true,show_tap_name:false,show_status:false,show_cocktail_select:false,show_details:true,show_glass:true,show_bubbles:true,show_progress:false,show_controls:false,show_time_on_tap:false,show_serving_tips:false,show_recipe:false},
        minimal: {compact:false,show_tap_name:true,show_status:true,show_cocktail_select:false,show_details:false,show_glass:false,show_bubbles:false,show_progress:false,show_controls:false,show_time_on_tap:false,show_serving_tips:false,show_recipe:false},
      };
      const presetName = event.target.value;
      const preset = presets[presetName];

      if (!preset) {
        this._emitConfig({ layout_preset: "custom" });
        return;
      }

      this._emitConfig({
        layout_preset: presetName,
        ...preset,
      });
      this._render();
    });

    this._value("recipe_mode")?.addEventListener("change", (event) => {
      this._emitConfig({
        layout_preset: "custom",
        recipe_mode: event.target.value,
      });
      this._render();
    });

    this._value("recipe_amount")?.addEventListener("change", (event) => {
      this._emitConfig({
        layout_preset: "custom",
        recipe_amount: event.target.value,
      });
      this._render();
    });

    [
      "show_tap_name",
      "show_status",
      "show_cocktail_select",
      "show_details",
      "show_glass",
      "show_bubbles",
      "show_progress",
      "show_controls",
      "show_time_on_tap",
      "show_shelf_life",
      "show_serving_tips",
      "show_recipe",
      "recipe_large_text",
      "compact",
    ].forEach((key) => {
      this._value(key)?.addEventListener("change", (event) => {
        this._emitConfig({
          layout_preset: "custom",
          [key]: event.target.checked,
        });
      });
    });
  }
}

if (!customElements.get("tapcocktail-card-editor")) {
  customElements.define("tapcocktail-card-editor", TapCocktailCardEditor);
}

if (!customElements.get("tapcocktail-card")) {
  customElements.define("tapcocktail-card", TapCocktailCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "tapcocktail-card",
  name: "TapCocktail Card",
  description: "Cocktailhane med layout-presets, opskrift, karbonering og live-forhåndsvisning.",
  preview: true,
});

/**
 * TapCocktail Library Card
 * Requires TapCocktail integration 2.1.0 or newer.
 *
 * Example:
 * type: custom:tapcocktail-library-card
 */
class TapCocktailLibraryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._library = { cocktails: {}, ingredients: {}, categories: { cocktail: [], ingredient: [] } };
    this._tab = "cocktails";
    this._search = "";
    this._category = "all";
    this._loading = true;
    this._error = "";
    this._dialog = null;
    this._saving = false;
    this._loaded = false;
    this._expandedCocktailId = null;
    this._showAllCocktails = false;
    this._showAllIngredients = false;
  }

  static getStubConfig() {
    return { title: "TapCocktail Bibliotek" };
  }

  setConfig(config) {
    this._config = {
      title: config?.title || "TapCocktail Bibliotek",
      entry_id: config?.entry_id || null,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded) this._load();
  }

  getCardSize() {
    return 8;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _items(value) {
    if (Array.isArray(value)) return value;
    return Object.values(value || {});
  }

  _command(type, extra = {}) {
    return {
      type,
      ...extra,
      ...(this._config.entry_id ? { entry_id: this._config.entry_id } : {}),
    };
  }

  async _load() {
    if (!this._hass) return;
    this._loaded = true;
    this._loading = true;
    this._error = "";
    this._render();
    try {
      const result = await this._hass.callWS(this._command("tapcocktail/library/get"));
      this._library = {
        cocktails: result?.cocktails || {},
        ingredients: result?.ingredients || {},
        categories: result?.categories || { cocktail: [], ingredient: [] },
      };
    } catch (error) {
      this._error = this._errorText(error);
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _errorText(error) {
    const code = error?.code || "";
    if (code === "unauthorized") return "Kun Home Assistant-administratorer kan bruge biblioteket.";
    if (code === "not_configured") return "TapCocktail er ikke konfigureret, eller der er flere installationer. Angiv entry_id i kortet.";
    return error?.message || error?.error || String(error || "Der opstod en ukendt fejl.");
  }

  _categoryItems(kind) {
    const categories = this._library.categories?.[kind];
    return Array.isArray(categories) ? categories : [];
  }

  _categoryName(kind, id) {
    const categoryId = String(id || (kind === "ingredient" ? "ukategoriseret" : "andre"));
    return this._categoryItems(kind).find((item) => String(item.id) === categoryId)?.name
      || categoryId.replaceAll("_", " ").replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  _filteredCocktails() {
    const needle = this._search.trim().toLocaleLowerCase("da");
    return this._items(this._library.cocktails)
      .filter((item) => this._category === "all" || (item.kategori || "andre") === this._category)
      .filter((item) => !needle || `${item.navn || ""} ${this._categoryName("cocktail", item.kategori)}`.toLocaleLowerCase("da").includes(needle))
      .sort((a, b) => String(a.navn || "").localeCompare(String(b.navn || ""), "da"));
  }

  _filteredIngredients() {
    const needle = this._search.trim().toLocaleLowerCase("da");
    return this._items(this._library.ingredients)
      .filter((item) => this._category === "all" || (item.category || "ukategoriseret") === this._category)
      .filter((item) => !needle || `${item.name || ""} ${item.id || ""} ${this._categoryName("ingredient", item.category)}`.toLocaleLowerCase("da").includes(needle))
      .sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "da"));
  }

  _shelfLife(item) {
    const days = item?.holdbarhed?.days;
    return days ? `${days} dage` : "Ikke angivet";
  }

  _renderCocktail(item) {
    const color = /^#[0-9a-f]{6}$/i.test(item.farve || "") ? item.farve : "#607d8b";
    const ingredients = Array.isArray(item.ingredienser) ? item.ingredienser.length : 0;
    const itemId = String(item.id);
    const expanded = this._expandedCocktailId === itemId;
    return `<article class="library-item cocktail-item ${expanded ? "expanded" : ""}" style="--accent:${this._escape(color)}">
      <div class="item-accent"></div>
      <div class="bubbles" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
      <button class="item-toggle" data-toggle-cocktail="${this._escape(itemId)}" aria-expanded="${expanded}">
        <div class="item-head">
          <div class="item-icon">${this._escape(item.ikon || "🍹")}</div>
          <div class="item-copy">
            <h3>${this._escape(item.navn || item.id)}</h3>
            <span class="category">${this._escape(this._categoryName("cocktail", item.kategori))}</span>
            <span class="compact-facts">${this._escape(item.abv ?? 0)} % ABV · ${this._escape(item.co2 ?? "–")} vol CO₂</span>
          </div>
          <ha-icon class="expand-icon" icon="mdi:chevron-down"></ha-icon>
        </div>
      </button>
      ${expanded ? `
        <div class="item-details">
          <div class="facts">
            <span><b>${this._escape(item.abv ?? 0)} %</b> ABV</span>
            <span><b>${this._escape(item.co2 ?? "–")}</b> vol CO₂</span>
            <span><b>${this._escape(item.temperatur ?? "–")} °C</b></span>
            <span><b>${ingredients}</b> ingredienser</span>
          </div>
          <div class="secondary">${this._escape(item.glas || "Glas ikke angivet")} · ${this._escape(this._shelfLife(item))}</div>
          <div class="item-actions">
            <button class="secondary-button" data-edit-cocktail="${this._escape(item.id)}">✏️ Rediger</button>
            <button class="danger-button" data-delete-cocktail="${this._escape(item.id)}">🗑️ Slet</button>
          </div>
        </div>
      ` : ""}
    </article>`;
  }

  _ingredientIcon(item) {
    const customIcon = String(item?.icon || "").trim();
    if (customIcon.startsWith("mdi:")) return customIcon;

    const category = String(item?.category || "").toLowerCase();
    const categoryIcons = [
      [["spiritus", "likør", "likor", "liqueur", "vin"], "mdi:bottle-wine"],
      [["sodavand", "soda", "mixer"], "mdi:bottle-soda"],
      [["juice", "citrus"], "mdi:fruit-citrus"],
      [["sirup", "syrup"], "mdi:bottle-tonic"],
      [["frugt", "bær", "baer"], "mdi:fruit-cherries"],
      [["vand", "water"], "mdi:water"],
      [["urt", "urter"], "mdi:leaf"],
      [["kaffe", "coffee"], "mdi:coffee"],
    ];
    const match = categoryIcons.find(([keywords]) => keywords.some((keyword) => category.includes(keyword)));
    return match?.[1] || (Number(item?.abv || 0) > 0 ? "mdi:bottle-wine" : "mdi:cup-water");
  }

  _renderIngredient(item) {
    return `<article class="library-item ingredient-item">
      <div class="ingredient-symbol"><ha-icon icon="${this._escape(this._ingredientIcon(item))}"></ha-icon></div>
      <div class="ingredient-copy"><h3>${this._escape(item.name || item.id)}</h3><span>${this._escape(this._categoryName("ingredient", item.category))}</span></div>
      <div class="abv-pill">${this._escape(item.abv ?? 0)} %</div>
      <div class="item-actions ingredient-actions">
        <button class="secondary-button" data-edit-ingredient="${this._escape(item.id)}" aria-label="Rediger ingrediens" title="Rediger"><ha-icon icon="mdi:pencil"></ha-icon></button>
        <button class="danger-button" data-delete-ingredient="${this._escape(item.id)}" aria-label="Slet ingrediens" title="Slet"><ha-icon icon="mdi:delete-outline"></ha-icon></button>
      </div>
    </article>`;
  }

  _field(label, name, value = "", options = {}) {
    const { type = "text", step = "any", min = "", max = "", required = false, placeholder = "" } = options;
    return `<label><span>${this._escape(label)}</span><input name="${name}" type="${type}" value="${this._escape(value)}" step="${step}" min="${min}" max="${max}" placeholder="${this._escape(placeholder)}" ${required ? "required" : ""}></label>`;
  }

  _select(label, name, value, options) {
    return `<label><span>${this._escape(label)}</span><select name="${name}">${options.map(([key, text]) => `<option value="${this._escape(key)}" ${String(key) === String(value) ? "selected" : ""}>${this._escape(text)}</option>`).join("")}</select></label>`;
  }

  _ingredientRow(item = {}) {
    const selected = item.bibliotek_id || "";
    const libraryOptions = [["", "Manuel ingrediens"], ...this._items(this._library.ingredients).map((ingredient) => [ingredient.id, ingredient.name])];
    return `<div class="ingredient-row">
      <button type="button" class="remove-row" title="Fjern ingrediens">×</button>
      ${this._select("Fra bibliotek", "ingredient_library", selected, libraryOptions)}
      ${this._field("Navn", "ingredient_name", item.navn || "", { required: true })}
      ${this._field("Alkohol %", "ingredient_abv", item.alkoholprocent ?? 0, { type: "number", min: 0, max: 100 })}
      ${this._field("Pr. glas", "ingredient_glass", item.glas || "", { required: true, placeholder: "fx 4 cl" })}
      ${this._field("2 liter", "ingredient_two", item["2_liter"] || "", { placeholder: "beregnes automatisk" })}
      ${this._field("9 liter", "ingredient_nine", item["9_liter"] || "", { placeholder: "beregnes automatisk" })}
    </div>`;
  }

  _cocktailDialog(item = null) {
    const editing = Boolean(item);
    const shelf = item?.holdbarhed || {};
    let shelfMode = String(shelf.mode || "none");
    if (!["none", "recommended", "3", "5", "7", "14", "30", "custom"].includes(shelfMode)) shelfMode = "custom";
    const rows = (item?.ingredienser?.length ? item.ingredienser : [{}]).map((ingredient) => this._ingredientRow(ingredient)).join("");
    return `<div class="overlay"><section class="dialog wide" role="dialog" aria-modal="true">
      <header><div><small>${editing ? "REDIGER" : "OPRET"}</small><h2>${editing ? this._escape(item.navn) : "Ny cocktail"}</h2></div><button class="icon-button close-dialog">×</button></header>
      <form id="cocktail-form" data-original-id="${this._escape(item?.id || "")}">
        <div class="form-grid">
          ${this._field("Navn", "navn", item?.navn || "", { required: true })}
          ${this._select("Kategori", "kategori", item?.kategori || this._categoryItems("cocktail")[0]?.id || "andre", this._categoryItems("cocktail").map((category) => [category.id, category.name]))}
          ${this._field("Tema", "tema", item?.tema || "klassisk", { required: true })}
          ${this._field("Ikon (valgfrit)", "ikon_override", item?.ikon || "", { placeholder: "🍹" })}
          ${this._field("Farve", "brugerdefineret_farve", item?.farve || "#7ED957", { type: "color" })}
          ${this._field("ABV %", "abv", item?.abv ?? 0, { type: "number", min: 0, max: 100 })}
          ${this._field("CO₂ vol", "co2", item?.co2 ?? 2.5, { type: "number", min: 0, max: 6, step: 0.1 })}
          ${this._field("Temperatur °C", "temperatur", item?.temperatur ?? 4, { type: "number", min: -10, max: 30, step: 0.5 })}
          ${this._field("Glas", "glas", item?.glas || "", { placeholder: "Highball" })}
          ${this._field("Karbonering timer", "karboneringstid_timer", item?.karbonering?.tid_timer ?? 24, { type: "number", min: 0, max: 168, step: 0.5 })}
          ${this._select("Holdbarhed", "holdbarhed_valg", shelfMode, [["none","Ingen"],["recommended","Anbefalet"],["3","3 dage"],["5","5 dage"],["7","7 dage"],["14","14 dage"],["30","30 dage"],["custom","Brugerdefineret"]])}
          ${this._field("Brugerdefinerede dage", "holdbarhed_dage", shelf.days || 7, { type: "number", min: 1, max: 3650 })}
          ${this._select("Beregn fra", "beregn_fra", item?.beregning?.source || "glass", [["glass","Pr. glas"],["two_liter","2 liter"],["nine_liter","9 liter"]])}
          <label class="checkbox"><input type="checkbox" name="automatisk_beregning" ${item?.beregning?.enabled !== false ? "checked" : ""}><span>Beregn mængder automatisk</span></label>
          <label class="checkbox"><input type="checkbox" name="automatisk_abv" ${item?.abv_beregning?.enabled ? "checked" : ""}><span>Beregn ABV automatisk</span></label>
        </div>
        <div class="section-title"><h3>Ingredienser</h3><button type="button" class="secondary-button add-row">＋ Tilføj ingrediens</button></div>
        <div id="ingredient-rows">${rows}</div>
        <div class="form-grid textareas">
          <label><span>Fremgangsmåde</span><textarea name="fremgangsmaade">${this._escape(item?.fremgangsmaade || "")}</textarea></label>
          <label><span>Pynt</span><textarea name="pynt">${this._escape(item?.pynt || "")}</textarea></label>
          <label><span>Serveringstips</span><textarea name="serveringstips">${this._escape(item?.serveringstips || "")}</textarea></label>
          <label><span>Noter</span><textarea name="noter">${this._escape(item?.noter || "")}</textarea></label>
        </div>
        <div class="dialog-error">${this._escape(this._error)}</div>
        <footer><button type="button" class="secondary-button close-dialog">Annuller</button><button class="primary-button" type="submit" ${this._saving ? "disabled" : ""}>${this._saving ? "Gemmer…" : "💾 Gem cocktail"}</button></footer>
      </form>
    </section></div>`;
  }

  _ingredientDialog(item = null) {
    return `<div class="overlay"><section class="dialog" role="dialog" aria-modal="true">
      <header><div><small>${item ? "REDIGER" : "OPRET"}</small><h2>${item ? this._escape(item.name) : "Ny ingrediens"}</h2></div><button class="icon-button close-dialog">×</button></header>
      <form id="ingredient-form" data-original-id="${this._escape(item?.id || "")}">
        ${this._field("Navn", "name", item?.name || "", { required: true })}
        ${this._field("ID", "id", item?.id || "", { required: true, placeholder: "fx passionsfrugt_sirup" })}
        ${this._select("Kategori", "category", item?.category || "ukategoriseret", this._categoryItems("ingredient").map((category) => [category.id, category.name]))}
        ${this._select("Ikon", "icon", item?.icon || "", [
          ["", "Automatisk ud fra kategori"],
          ["mdi:bottle-wine", "Flaske / spiritus"],
          ["mdi:bottle-soda", "Sodavand"],
          ["mdi:fruit-citrus", "Juice / citrus"],
          ["mdi:bottle-tonic", "Sirup"],
          ["mdi:fruit-cherries", "Frugt / bær"],
          ["mdi:water", "Vand"],
          ["mdi:leaf", "Urter"],
          ["mdi:coffee", "Kaffe"],
          ["mdi:cup-water", "Drik / andet"],
        ])}
        ${this._field("Alkoholprocent", "abv", item?.abv ?? 0, { type: "number", min: 0, max: 100, step: 0.1, required: true })}
        <div class="dialog-error">${this._escape(this._error)}</div>
        <footer><button type="button" class="secondary-button close-dialog">Annuller</button><button class="primary-button" type="submit" ${this._saving ? "disabled" : ""}>${this._saving ? "Gemmer…" : "💾 Gem ingrediens"}</button></footer>
      </form>
    </section></div>`;
  }

  _categoryDialog(kind, item = null) {
    const categories = this._categoryItems(kind);
    const label = kind === "cocktail" ? "cocktailkategorier" : "ingredienskategorier";
    const rows = categories.map((category) => `
      <div class="category-row">
        <div><b>${this._escape(category.name)}</b><span>${this._escape(category.id)}</span></div>
        <button type="button" class="secondary-button edit-category" data-category-id="${this._escape(category.id)}">✏️</button>
        <button type="button" class="danger-button delete-category" data-category-id="${this._escape(category.id)}">🗑️</button>
      </div>`).join("");
    return `<div class="overlay"><section class="dialog" role="dialog" aria-modal="true">
      <header><div><small>KATEGORIER</small><h2>Administrér ${label}</h2></div><button class="icon-button close-dialog">×</button></header>
      <div class="category-list">${rows || '<p class="hint">Ingen kategorier oprettet endnu.</p>'}</div>
      <form id="category-form" data-kind="${kind}" data-original-id="${this._escape(item?.id || "")}">
        <h3>${item ? "Omdøb kategori" : "Opret ny kategori"}</h3>
        ${this._field("Navn", "name", item?.name || "", { required: true, placeholder: "fx Spiritus" })}
        <div class="dialog-error">${this._escape(this._error)}</div>
        <footer>
          ${item ? '<button type="button" class="secondary-button cancel-category-edit">Annuller redigering</button>' : ""}
          <button class="primary-button" type="submit" ${this._saving ? "disabled" : ""}>${this._saving ? "Gemmer…" : item ? "💾 Gem navn" : "＋ Opret kategori"}</button>
        </footer>
      </form>
    </section></div>`;
  }

  _deleteDialog(kind, item) {
    const name = kind === "cocktail" ? item.navn : item.name;
    return `<div class="overlay"><section class="dialog confirm" role="alertdialog" aria-modal="true">
      <div class="delete-icon">🗑️</div><h2>Slet ${kind === "cocktail" ? "cocktail" : "ingrediens"}?</h2>
      <p><b>${this._escape(name)}</b> bliver slettet permanent.</p>
      ${kind === "ingredient" ? "<p class=hint>Eksisterende cocktails beholder deres gemte ingrediensdata.</p>" : ""}
      <div class="dialog-error">${this._escape(this._error)}</div>
      <footer><button class="secondary-button close-dialog">Annuller</button><button class="danger-button confirm-delete" data-kind="${kind}" data-id="${this._escape(item.id)}" ${this._saving ? "disabled" : ""}>${this._saving ? "Sletter…" : "Ja, slet"}</button></footer>
    </section></div>`;
  }

  _styles() {
    return `<style>
      :host{display:block;font-family:var(--paper-font-body1_-_font-family,Arial,sans-serif);color:var(--primary-text-color)}*{box-sizing:border-box}ha-card{position:relative;overflow:hidden;padding:20px;border-radius:24px;background:var(--ha-card-background,var(--card-background-color,#fff))}.topbar,.tabs,.tools,.grid,.list-toggle,.state,.empty{position:relative;z-index:2}.card-bubbles{position:absolute;z-index:1;inset:0;pointer-events:none;overflow:hidden;opacity:.18}.card-bubbles i{position:absolute;bottom:-50px;width:36px;height:36px;border:3px solid color-mix(in srgb,var(--primary-color,#03a9f4) 55%,var(--divider-color,#ddd) 45%);border-radius:50%;animation:card-bubble-rise 13s linear infinite}.card-bubbles i:nth-child(1){left:5%;width:48px;height:48px;animation-delay:-3s}.card-bubbles i:nth-child(2){left:24%;width:28px;height:28px;animation-delay:-9s;animation-duration:11s}.card-bubbles i:nth-child(3){left:47%;width:58px;height:58px;animation-delay:-6s;animation-duration:16s}.card-bubbles i:nth-child(4){left:70%;width:38px;height:38px;animation-delay:-12s;animation-duration:14s}.card-bubbles i:nth-child(5){left:88%;width:24px;height:24px;animation-delay:-5s;animation-duration:10s}@keyframes card-bubble-rise{0%{transform:translateY(0) scale(.75);opacity:0}12%{opacity:.8}82%{opacity:.45}100%{transform:translateY(-900px) scale(1.18);opacity:0}}.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px}.title-wrap small,.dialog small{font-size:10px;font-weight:900;letter-spacing:.16em;color:var(--secondary-text-color)}h1,h2,h3,p{margin:0}.topbar h1{font-size:24px;margin-top:3px}.icon-button{width:42px;height:42px;border:0;border-radius:50%;font-size:24px;background:color-mix(in srgb,var(--primary-text-color) 8%,transparent);color:inherit}.tabs{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:20px 0 14px;padding:5px;border-radius:16px;background:color-mix(in srgb,var(--primary-text-color) 7%,transparent)}.tab{border:0;border-radius:12px;padding:11px;background:transparent;color:var(--secondary-text-color);font-weight:800}.tab.active{color:var(--primary-text-color);background:var(--card-background-color,#fff);box-shadow:0 2px 10px #0002}.tools{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:10px;margin-bottom:18px}.tools input,.tools select{min-height:44px;border:1px solid var(--divider-color,#ddd);border-radius:13px;padding:0 12px;background:var(--card-background-color,#fff);color:inherit;font:inherit}.primary-button,.secondary-button,.danger-button{border:0;border-radius:12px;min-height:40px;padding:0 14px;font:inherit;font-weight:800;cursor:pointer}.primary-button{background:var(--primary-color,#03a9f4);color:var(--text-primary-color,#fff)}.secondary-button{background:color-mix(in srgb,var(--primary-text-color) 9%,transparent);color:inherit}.danger-button{background:color-mix(in srgb,#f44336 14%,transparent);color:#d32f2f}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:10px}.library-item{position:relative;border:1px solid var(--divider-color,#ddd);border-radius:18px;padding:14px;background:color-mix(in srgb,var(--card-background-color,#fff) 97%,var(--primary-text-color) 3%);overflow:hidden}.item-accent{position:absolute;z-index:2;inset:0 auto 0 0;width:5px;background:var(--accent)}.item-toggle{position:relative;z-index:2;width:100%;padding:0;border:0;background:transparent;color:inherit;text-align:left;cursor:pointer}.item-head{display:flex;align-items:center;gap:12px}.item-copy{min-width:0;flex:1}.item-icon{width:48px;height:48px;flex:0 0 48px;border-radius:50%;display:grid;place-items:center;font-size:26px;background:color-mix(in srgb,var(--accent) 25%,transparent)}.item-head h3,.ingredient-copy h3{font-size:17px}.category,.secondary,.ingredient-copy span{font-size:12px;color:var(--secondary-text-color)}.category{display:block}.compact-facts{display:block;margin-top:3px;font-size:11px;color:var(--secondary-text-color)}.expand-icon{transition:transform .2s ease;color:var(--secondary-text-color)}.cocktail-item.expanded .expand-icon{transform:rotate(180deg)}.cocktail-item.expanded .bubbles{opacity:.48}.cocktail-item.expanded .bubbles i{width:28px;height:28px;border-width:2px}.item-details{position:relative;z-index:2;animation:details-in .18s ease}.bubbles{position:absolute;z-index:1;inset:0;pointer-events:none;overflow:hidden;opacity:.34}.bubbles i{position:absolute;bottom:-18px;width:10px;height:10px;border:1.5px solid color-mix(in srgb,var(--accent) 75%,var(--primary-text-color) 25%);border-radius:50%;animation:bubble-rise 6s linear infinite}.bubbles i:nth-child(1){left:14%;width:7px;height:7px;animation-delay:-1s}.bubbles i:nth-child(2){left:38%;width:12px;height:12px;animation-delay:-4s;animation-duration:7s}.bubbles i:nth-child(3){left:62%;width:8px;height:8px;animation-delay:-2.5s;animation-duration:5.5s}.bubbles i:nth-child(4){left:78%;width:14px;height:14px;animation-delay:-5s;animation-duration:8s}.bubbles i:nth-child(5){left:91%;width:6px;height:6px;animation-delay:-3s;animation-duration:5s}@keyframes bubble-rise{0%{transform:translateY(0) scale(.7);opacity:0}15%{opacity:.75}85%{opacity:.45}100%{transform:translateY(-190px) scale(1.2);opacity:0}}@keyframes details-in{from{opacity:0;transform:translateY(-5px)}to{opacity:1;transform:translateY(0)}}.facts{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:15px 0;font-size:12px}.facts span{padding:8px;border-radius:10px;background:color-mix(in srgb,var(--primary-text-color) 6%,transparent)}.facts b{display:block;font-size:14px}.item-actions{display:flex;gap:8px;margin-top:15px}.item-actions button{flex:1}.ingredient-item{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px}.ingredient-symbol{width:34px;height:34px;display:grid;place-items:center;color:var(--primary-color);}.ingredient-symbol ha-icon{--mdc-icon-size:27px}.ingredient-actions ha-icon{--mdc-icon-size:20px}.abv-pill{font-weight:900;padding:7px 10px;border-radius:99px;background:color-mix(in srgb,var(--primary-text-color) 9%,transparent);color:var(--primary-text-color)}.ingredient-actions{grid-column:1/-1;margin-top:3px}.category-list{display:grid;gap:8px;margin-bottom:22px}.category-row{display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:8px;padding:10px;border:1px solid var(--divider-color,#ddd);border-radius:12px}.category-row span{display:block;margin-top:2px;font-size:11px;color:var(--secondary-text-color)}#category-form{padding-top:18px;border-top:1px solid var(--divider-color,#ddd)}#category-form h3{margin-bottom:14px}.list-toggle{display:block;width:100%;margin-top:12px}.state,.empty{text-align:center;padding:42px 12px;color:var(--secondary-text-color)}.error{color:#d32f2f}.overlay{position:fixed;z-index:9999;inset:0;display:grid;place-items:center;padding:16px;background:#0009}.dialog{width:min(480px,100%);max-height:92vh;overflow:auto;padding:22px;border-radius:22px;background:var(--card-background-color,#fff);box-shadow:0 20px 80px #0008}.dialog.wide{width:min(940px,100%)}.dialog header{display:flex;justify-content:space-between;align-items:start;margin-bottom:20px}.dialog h2{margin-top:4px}.dialog form>label,.form-grid label,.ingredient-row label,.textareas label{display:flex;flex-direction:column;gap:6px;margin-bottom:14px;font-size:12px;font-weight:800;color:var(--secondary-text-color)}.dialog input,.dialog select,.dialog textarea{width:100%;min-height:43px;border:1px solid var(--divider-color,#ddd);border-radius:11px;padding:9px 11px;background:var(--card-background-color,#fff);color:var(--primary-text-color);font:inherit}.dialog textarea{min-height:82px;resize:vertical}.form-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:0 12px}.checkbox{flex-direction:row!important;align-items:center!important;margin-top:22px}.checkbox input{width:20px;height:20px;min-height:0}.section-title{display:flex;align-items:center;justify-content:space-between;margin:12px 0}.ingredient-row{position:relative;display:grid;grid-template-columns:1.2fr 1.2fr .65fr .7fr .8fr .8fr;gap:8px;padding:15px 8px 2px;border-top:1px solid var(--divider-color,#ddd)}.remove-row{position:absolute;right:-4px;top:-8px;width:26px;height:26px;border:0;border-radius:50%;background:#f44336;color:white;font-size:20px}.textareas{grid-template-columns:1fr 1fr;margin-top:18px}.dialog footer{display:flex;justify-content:flex-end;gap:10px;margin-top:20px}.dialog-error{min-height:18px;margin-top:8px;color:#d32f2f;font-size:13px;font-weight:700}.confirm{text-align:center}.delete-icon{font-size:44px;margin-bottom:12px}.confirm p{margin-top:10px}.hint{font-size:12px;color:var(--secondary-text-color)}button:disabled{opacity:.55;cursor:wait}
      @media(max-width:700px){ha-card{padding:14px;border-radius:18px}.topbar h1{font-size:20px}.tools{grid-template-columns:1fr auto}.tools select{grid-row:2}.tools .manage-categories{grid-column:1}.tools .primary-button{grid-column:2;grid-row:1/3}.grid{grid-template-columns:1fr}.form-grid,.textareas{grid-template-columns:1fr 1fr}.ingredient-row{grid-template-columns:1fr 1fr}.dialog{padding:17px}.ingredient-row label:first-of-type,.ingredient-row label:nth-of-type(2){grid-column:span 1}}
      @media(max-width:450px){.form-grid,.textareas,.ingredient-row{grid-template-columns:1fr}.tools{grid-template-columns:1fr}.tools .primary-button,.tools select{grid-column:auto;grid-row:auto}.primary-button{padding:0 10px}.topbar{align-items:start}}
    </style>`;
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;
    const cocktailTab = this._tab === "cocktails";
    const allItems = cocktailTab ? this._filteredCocktails() : this._filteredIngredients();
    const showAll = cocktailTab ? this._showAllCocktails : this._showAllIngredients;
    const hiddenItemCount = Math.max(0, allItems.length - 3);
    const items = showAll ? allItems : allItems.slice(0, 3);
    const categoryKind = cocktailTab ? "cocktail" : "ingredient";
    const categoryOptions = this._categoryItems(categoryKind).map((category) => `<option value="${this._escape(category.id)}" ${this._category === category.id ? "selected" : ""}>${this._escape(category.name)}</option>`).join("");
    let content = "";
    if (this._loading) content = '<div class="state">Indlæser bibliotek…</div>';
    else if (this._error && !this._dialog) content = `<div class="state error">${this._escape(this._error)}<br><br><button class="secondary-button retry">Prøv igen</button></div>`;
    else if (!items.length) content = '<div class="empty">Ingen resultater fundet.</div>';
    else content = `<div class="grid">${items.map((item) => cocktailTab ? this._renderCocktail(item) : this._renderIngredient(item)).join("")}</div>${allItems.length > 3 ? `<button class="secondary-button list-toggle">${showAll ? "Vis færre" : `Vis resten (${hiddenItemCount})`}</button>` : ""}`;
    let dialog = "";
    if (this._dialog?.type === "cocktail") dialog = this._cocktailDialog(this._dialog.item);
    if (this._dialog?.type === "ingredient") dialog = this._ingredientDialog(this._dialog.item);
    if (this._dialog?.type === "delete") dialog = this._deleteDialog(this._dialog.kind, this._dialog.item);
    if (this._dialog?.type === "categories") dialog = this._categoryDialog(this._dialog.kind, this._dialog.item);
    this.shadowRoot.innerHTML = `${this._styles()}<ha-card>
      <div class="card-bubbles" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
      <div class="topbar"><div class="title-wrap"><h1>${this._escape(this._config.title)}</h1></div><button class="icon-button refresh" title="Genindlæs">↻</button></div>
      <div class="tabs"><button class="tab ${cocktailTab ? "active" : ""}" data-tab="cocktails">🍹 Cocktails <span>(${this._items(this._library.cocktails).length})</span></button><button class="tab ${!cocktailTab ? "active" : ""}" data-tab="ingredients">🧴 Ingredienser <span>(${this._items(this._library.ingredients).length})</span></button></div>
      <div class="tools"><input class="search" type="search" value="${this._escape(this._search)}" placeholder="Søg i ${cocktailTab ? "cocktails" : "ingredienser"}…"><select class="category-filter"><option value="all">Alle kategorier</option>${categoryOptions}</select><button class="secondary-button manage-categories">⚙️ Kategorier</button><button class="primary-button create">＋ Opret ${cocktailTab ? "cocktail" : "ingrediens"}</button></div>
      ${content}
    </ha-card>${dialog}`;
    this._bind();
  }

  _find(kind, id) {
    const source = kind === "cocktail" ? this._library.cocktails : this._library.ingredients;
    return this._items(source).find((item) => String(item.id) === String(id));
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => { this._tab = button.dataset.tab; this._search = ""; this._category = "all"; this._showAllCocktails = false; this._showAllIngredients = false; this._render(); }));
    root.querySelector(".search")?.addEventListener("input", (event) => { this._search = event.target.value; this._showAllCocktails = false; this._showAllIngredients = false; this._render(); root.querySelector(".search")?.focus(); });
    root.querySelector(".category-filter")?.addEventListener("change", (event) => { this._category = event.target.value; this._showAllCocktails = false; this._showAllIngredients = false; this._render(); });
    root.querySelector(".refresh")?.addEventListener("click", () => { this._loaded = false; this._load(); });
    root.querySelector(".retry")?.addEventListener("click", () => { this._loaded = false; this._load(); });
    root.querySelector(".list-toggle")?.addEventListener("click", () => { if (this._tab === "cocktails") { this._showAllCocktails = !this._showAllCocktails; if (!this._showAllCocktails) this._expandedCocktailId = null; } else { this._showAllIngredients = !this._showAllIngredients; } this._render(); });
    root.querySelector(".manage-categories")?.addEventListener("click", () => { this._error = ""; this._dialog = { type: "categories", kind: this._tab === "cocktails" ? "cocktail" : "ingredient", item: null }; this._render(); });
    root.querySelector(".create")?.addEventListener("click", () => { this._error = ""; this._dialog = { type: this._tab === "cocktails" ? "cocktail" : "ingredient", item: null }; this._render(); });
    root.querySelectorAll("[data-toggle-cocktail]").forEach((button) => button.addEventListener("click", () => { const id = button.dataset.toggleCocktail; this._expandedCocktailId = this._expandedCocktailId === id ? null : id; this._render(); }));
    root.querySelectorAll("[data-edit-cocktail]").forEach((button) => button.addEventListener("click", () => { this._error = ""; this._dialog = { type: "cocktail", item: this._find("cocktail", button.dataset.editCocktail) }; this._render(); }));
    root.querySelectorAll("[data-edit-ingredient]").forEach((button) => button.addEventListener("click", () => { this._error = ""; this._dialog = { type: "ingredient", item: this._find("ingredient", button.dataset.editIngredient) }; this._render(); }));
    root.querySelectorAll("[data-delete-cocktail]").forEach((button) => button.addEventListener("click", () => { this._error = ""; this._dialog = { type: "delete", kind: "cocktail", item: this._find("cocktail", button.dataset.deleteCocktail) }; this._render(); }));
    root.querySelectorAll("[data-delete-ingredient]").forEach((button) => button.addEventListener("click", () => { this._error = ""; this._dialog = { type: "delete", kind: "ingredient", item: this._find("ingredient", button.dataset.deleteIngredient) }; this._render(); }));
    root.querySelectorAll(".close-dialog").forEach((button) => button.addEventListener("click", () => { this._dialog = null; this._error = ""; this._render(); }));
    root.querySelector(".add-row")?.addEventListener("click", () => { root.querySelector("#ingredient-rows").insertAdjacentHTML("beforeend", this._ingredientRow()); this._bindIngredientRows(); });
    this._bindIngredientRows();
    root.querySelector("#cocktail-form")?.addEventListener("submit", (event) => this._saveCocktail(event));
    root.querySelector("#ingredient-form")?.addEventListener("submit", (event) => this._saveIngredient(event));
    root.querySelector("#category-form")?.addEventListener("submit", (event) => this._saveCategory(event));
    root.querySelectorAll(".edit-category").forEach((button) => button.addEventListener("click", () => {
      const kind = this._dialog.kind;
      const item = this._categoryItems(kind).find((category) => String(category.id) === button.dataset.categoryId);
      this._dialog = { type: "categories", kind, item }; this._error = ""; this._render();
    }));
    root.querySelectorAll(".delete-category").forEach((button) => button.addEventListener("click", () => this._deleteCategory(this._dialog.kind, button.dataset.categoryId)));
    root.querySelector(".cancel-category-edit")?.addEventListener("click", () => { this._dialog = { type: "categories", kind: this._dialog.kind, item: null }; this._error = ""; this._render(); });
    root.querySelector(".confirm-delete")?.addEventListener("click", (event) => this._delete(event.currentTarget.dataset.kind, event.currentTarget.dataset.id));
  }

  _bindIngredientRows() {
    const root = this.shadowRoot;
    root.querySelectorAll(".ingredient-row").forEach((row) => {
      row.querySelector(".remove-row")?.addEventListener("click", () => { if (root.querySelectorAll(".ingredient-row").length > 1) row.remove(); });
      row.querySelector('[name="ingredient_library"]')?.addEventListener("change", (event) => {
        const ingredient = this._find("ingredient", event.target.value);
        if (!ingredient) return;
        row.querySelector('[name="ingredient_name"]').value = ingredient.name;
        row.querySelector('[name="ingredient_abv"]').value = ingredient.abv;
      });
    });
  }

  _cocktailData(form) {
    const data = Object.fromEntries(new FormData(form).entries());
    data.automatisk_beregning = form.elements.automatisk_beregning.checked;
    data.automatisk_abv = form.elements.automatisk_abv.checked;
    data.ingredienser = [...form.querySelectorAll(".ingredient-row")].map((row) => ({
      bibliotek_id: row.querySelector('[name="ingredient_library"]').value || undefined,
      navn: row.querySelector('[name="ingredient_name"]').value.trim(),
      alkoholprocent: Number(row.querySelector('[name="ingredient_abv"]').value || 0),
      glas: row.querySelector('[name="ingredient_glass"]').value.trim(),
      "2_liter": row.querySelector('[name="ingredient_two"]').value.trim(),
      "9_liter": row.querySelector('[name="ingredient_nine"]').value.trim(),
    })).filter((item) => item.navn);
    return data;
  }

  async _saveCocktail(event) {
    event.preventDefault();
    const form = event.currentTarget;
    this._saving = true; this._error = ""; this._render();
    try {
      await this._hass.callWS(this._command("tapcocktail/cocktail/save", { data: this._cocktailData(form), ...(form.dataset.originalId ? { original_id: form.dataset.originalId } : {}) }));
      this._dialog = null; this._loaded = false; await this._load();
    } catch (error) { this._error = this._errorText(error); this._render(); }
    finally { this._saving = false; }
  }

  async _saveIngredient(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    values.abv = Number(values.abv);
    this._saving = true; this._error = ""; this._render();
    try {
      await this._hass.callWS(this._command("tapcocktail/ingredient/save", { data: values, ...(form.dataset.originalId ? { original_id: form.dataset.originalId } : {}) }));
      this._dialog = null; this._loaded = false; await this._load();
    } catch (error) { this._error = this._errorText(error); this._render(); }
    finally { this._saving = false; }
  }

  async _saveCategory(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const kind = form.dataset.kind;
    const values = Object.fromEntries(new FormData(form).entries());
    this._saving = true; this._error = ""; this._render();
    try {
      await this._hass.callWS(this._command("tapcocktail/category/save", {
        kind,
        data: values,
        ...(form.dataset.originalId ? { original_id: form.dataset.originalId } : {}),
      }));
      this._loaded = false;
      await this._load();
      this._dialog = { type: "categories", kind, item: null };
      this._render();
    } catch (error) { this._error = this._errorText(error); this._render(); }
    finally { this._saving = false; }
  }

  async _deleteCategory(kind, categoryId) {
    const category = this._categoryItems(kind).find((item) => String(item.id) === String(categoryId));
    if (!window.confirm(`Slet kategorien "${category?.name || categoryId}"? Kategorien kan kun slettes, hvis den ikke bruges.`)) return;
    this._saving = true; this._error = ""; this._render();
    try {
      await this._hass.callWS(this._command("tapcocktail/category/delete", { kind, category_id: categoryId, confirm: true }));
      if (this._category === categoryId) this._category = "all";
      this._loaded = false;
      await this._load();
      this._dialog = { type: "categories", kind, item: null };
      this._render();
    } catch (error) { this._error = this._errorText(error); this._render(); }
    finally { this._saving = false; }
  }

  async _delete(kind, id) {
    this._saving = true; this._error = ""; this._render();
    try {
      const type = kind === "cocktail" ? "tapcocktail/cocktail/delete" : "tapcocktail/ingredient/delete";
      const key = kind === "cocktail" ? "cocktail_id" : "ingredient_id";
      await this._hass.callWS(this._command(type, { [key]: id, confirm: true }));
      this._dialog = null; this._loaded = false; await this._load();
    } catch (error) { this._error = this._errorText(error); this._render(); }
    finally { this._saving = false; }
  }
}

if (!customElements.get("tapcocktail-library-card")) {
  customElements.define("tapcocktail-library-card", TapCocktailLibraryCard);
}

window.customCards.push({
  type: "tapcocktail-library-card",
  name: "TapCocktail Library Card",
  description: "Administrér cocktails og ingredienser direkte fra Home Assistant-dashboardet.",
  preview: true,
});
