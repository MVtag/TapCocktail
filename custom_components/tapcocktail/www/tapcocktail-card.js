/** TapCocktail Card v1.6.1 - HACS review hardening */
import "./tapcocktail-card-core.js";

const Card = customElements.get("tapcocktail-card");
const Editor = customElements.get("tapcocktail-card-editor");
const invalid = new Set(["", "unknown", "unavailable", "none"]);
const BUBBLE_MIN_CO2 = 2.0;
const BUBBLE_MAX_CO2 = 4.0;

if (Card && !Card.__pressurePlan) {
  Card.__pressurePlan = true;
  const p = Card.prototype;
  const oldConfig = p.setConfig;
  const oldIds = p._entityIds;
  const oldRender = p._render;
  const oldStub = Card.getStubConfig?.bind(Card);

  p.setConfig = function (config) {
    return oldConfig.call(this, { show_pressure_plan: true, ...config });
  };

  p._entityIds = function () {
    const ids = oldIds.call(this);
    const tap = this._config?.tap ?? 1;
    return {
      ...ids,
      carbonationPressure: `sensor.hane_${tap}_karboneringstryk`,
      coolingPressure: `sensor.hane_${tap}_koletryk`,
      servingPressure: `sensor.hane_${tap}_serveringstryk`,
    };
  };

  p._pressureValue = function (value, digits) {
    const number = Number(value);
    return Number.isFinite(number)
      ? number.toLocaleString("da-DK", {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits,
        })
      : null;
  };

  p._pressureData = function (entity) {
    const attrs = entity?.attributes ?? {};
    const state = String(entity?.state ?? "").toLowerCase();
    const bar = this._pressureValue(entity?.state, 2);
    return {
      ready:
        Boolean(entity) &&
        !invalid.has(state) &&
        bar !== null &&
        attrs.status !== "mangler_karboneringsrum_temperatur",
      bar,
      psi: this._pressureValue(attrs.psi, 1),
      temp: this._pressureValue(attrs.temperatur, 1),
      source: String(attrs.temperatur_kilde ?? ""),
    };
  };

  p._renderExtendedBubbles = function () {
    const root = this.shadowRoot;
    const container = root?.querySelector(".bubbles");
    if (!container || !this._hass || !this._config) return;

    const ids = this._entityIds();
    const cocktailEntity = this._state(ids.cocktail);
    const libraryEntity = this._state(ids.library);
    const previewCocktail =
      this._config.preview_cocktail_id &&
      libraryEntity?.attributes?.cocktails?.[this._config.preview_cocktail_id];
    const attrs =
      previewCocktail && typeof previewCocktail === "object"
        ? previewCocktail
        : cocktailEntity?.attributes ?? {};

    const rawCo2 = Number(attrs.co2 ?? attrs.vol_co2 ?? BUBBLE_MIN_CO2);
    const co2 = Number.isFinite(rawCo2) ? rawCo2 : BUBBLE_MIN_CO2;
    const clampedCo2 = Math.max(BUBBLE_MIN_CO2, Math.min(BUBBLE_MAX_CO2, co2));
    const bubbleLevel = Math.max(
      0,
      Math.min(
        1,
        (clampedCo2 - BUBBLE_MIN_CO2) /
          (BUBBLE_MAX_CO2 - BUBBLE_MIN_CO2)
      )
    );

    const bubbleCount = Math.round(18 + bubbleLevel * 26);
    const bubbleScale = (1.05 + bubbleLevel * 0.40).toFixed(2);
    const bubbleBaseDuration = 8.0 - bubbleLevel * 3.2;

    container.style.transform = `scale(${bubbleScale})`;
    container.innerHTML = Array.from({ length: bubbleCount }, (_, index) => {
      const left = (index * 17 + 7) % 100;
      const size = 10 + ((index * 5) % 18);
      const speed = Math.max(
        4.0,
        bubbleBaseDuration + (((index * 7) % 9) - 4) * 0.24
      ).toFixed(2);
      const delay = -((index * 1.26) % 10).toFixed(2);

      return `<span class="bubble" style="left:${left}%;--size:${size}px;--speed:${speed}s;--delay:${delay}s"></span>`;
    }).join("");
  };

  p._renderPressurePlan = function () {
    const root = this.shadowRoot;
    if (!root) return;
    root.querySelector(".tc-pressure-plan")?.remove();

    if (
      !this._hass ||
      !this._config ||
      this._config.compact ||
      this._config.show_pressure_plan === false
    ) return;

    const ids = this._entityIds();
    const cocktail = this._state(ids.cocktail);
    const cocktailState = String(cocktail?.state ?? "").toLowerCase();
    if (!cocktail || invalid.has(cocktailState) || cocktailState === "ingen") return;

    const carbonation = this._pressureData(this._state(ids.carbonationPressure));
    const cooling = this._pressureData(this._state(ids.coolingPressure));
    const serving = this._pressureData(this._state(ids.servingPressure));
    const status = String(this._state(ids.status)?.state ?? "idle").toLowerCase();
    const coolingStates = new Set(["cooling", "cooling_down", "nedkoling", "nedkøling"]);
    const co2 = this._pressureValue(
      cocktail.attributes?.co2 ??
        cocktail.attributes?.vol_co2 ??
        this._state(ids.carbonationPressure)?.attributes?.vol_co2,
      1
    );

    const activeStep =
      status === "carbonating"
        ? "carbonation"
        : coolingStates.has(status)
          ? "cooling"
          : status === "ready"
            ? "serving"
            : null;

    const sourceLabel = (source) => ({
      karboneringsrum: "Fælles rumføler",
      "opskriftens måltemperatur": "Opskriftens måltemperatur",
      "hanens temperatursensor": "Hanens temperaturføler",
    })[source] ?? source;

    const row = (key, number, name, icon, data, missing) => {
      const temp = data.ready && data.temp ? `${data.temp} °C` : missing;
      const pressure = data.ready && data.bar ? `${data.bar} bar` : "–";
      return `
        <div class="tc-pressure-row ${activeStep === key ? "active" : ""}">
          <div class="tc-pressure-number"><span>${number}</span></div>
          <div class="tc-pressure-label">
            <ha-icon icon="${icon}"></ha-icon>
            <span>${name}</span>
          </div>
          <div class="tc-pressure-temp">${this._escape(temp)}</div>
          <div class="tc-pressure-bar">${pressure}</div>
        </div>`;
    };

    const detailRow = (name, data, missing) => {
      const detail = data.ready
        ? `${data.psi ?? "–"} psi${data.source ? ` · ${sourceLabel(data.source)}` : ""}`
        : missing;
      return `<div class="tc-pressure-detail-row"><span>${name}</span><strong>${this._escape(detail)}</strong></div>`;
    };

    let actionText = "";
    let actionIcon = "mdi:information-outline";

    if (!carbonation.ready) {
      actionText = "Vælg den fælles rumføler for at beregne karboneringstrykket.";
      actionIcon = "mdi:alert-circle-outline";
    } else if (status === "carbonating") {
      actionText = cooling.ready
        ? `Når karboneringen er færdig: Sæt fadet på køl → ${cooling.bar} bar`
        : "Når karboneringen er færdig: Sæt fadet på køl.";
      actionIcon = "mdi:snowflake";
    } else if (coolingStates.has(status)) {
      actionText = cooling.ready
        ? `Køler ned mod ${cooling.temp ?? "måltemperaturen"} °C · ${cooling.bar} bar`
        : "Fadet køler ned mod serveringstemperaturen.";
      actionIcon = "mdi:snowflake-thermometer";
    } else if (status === "ready") {
      actionText = serving.ready
        ? `Klar til servering · Anbefalet tryk ${serving.bar} bar`
        : "Klar til servering.";
      actionIcon = "mdi:check-circle-outline";
    } else {
      actionText = cooling.ready
        ? `Start ved ${carbonation.bar} bar · På køl: ${cooling.bar} bar`
        : `Start karbonering ved ${carbonation.bar} bar`;
      actionIcon = "mdi:gauge";
    }

    if (!root.querySelector("style[data-tc-pressure]")) {
      const style = document.createElement("style");
      style.dataset.tcPressure = "";
      style.textContent = `
        .tc-pressure-plan{
          margin-top:14px;
          padding:13px 14px 10px;
          border-radius:16px;
          border:1px solid color-mix(in srgb,var(--cocktail-color) 25%,transparent);
          background:color-mix(in srgb,var(--cocktail-color) 7%,var(--card-background-color));
        }
        .tc-pressure-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px}
        .tc-pressure-title{font-size:13px;font-weight:900;letter-spacing:.055em;text-transform:uppercase}
        .tc-pressure-target{padding:4px 8px;border-radius:999px;font-size:11px;font-weight:800;background:color-mix(in srgb,var(--cocktail-color) 16%,transparent);white-space:nowrap}
        .tc-pressure-rows{display:grid;gap:2px}
        .tc-pressure-row{display:grid;grid-template-columns:24px minmax(0,1fr) auto auto;align-items:center;gap:8px;min-height:38px;padding:5px 7px;border-radius:11px;color:var(--secondary-text-color)}
        .tc-pressure-row.active{background:color-mix(in srgb,var(--cocktail-color) 16%,transparent);color:var(--primary-text-color)}
        .tc-pressure-number{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;font-size:10px;font-weight:900;background:color-mix(in srgb,var(--primary-text-color) 7%,transparent)}
        .tc-pressure-row.active .tc-pressure-number{background:color-mix(in srgb,var(--cocktail-color) 35%,transparent)}
        .tc-pressure-label{display:flex;align-items:center;gap:6px;min-width:0;font-size:12px;font-weight:800;color:var(--primary-text-color)}
        .tc-pressure-label ha-icon{--mdc-icon-size:16px;opacity:.82}
        .tc-pressure-temp{font-size:11px;white-space:nowrap}
        .tc-pressure-bar{font-size:13px;font-weight:900;color:var(--primary-text-color);white-space:nowrap;text-align:right}
        .tc-pressure-action{display:flex;align-items:center;gap:7px;margin-top:8px;padding:8px 9px;border-radius:10px;background:color-mix(in srgb,var(--primary-text-color) 5%,transparent);font-size:11px;line-height:1.35;color:var(--secondary-text-color)}
        .tc-pressure-action ha-icon{--mdc-icon-size:16px;flex:0 0 auto;color:var(--primary-text-color)}
        .tc-pressure-toggle{display:flex;align-items:center;gap:4px;margin:5px auto -1px;padding:5px 8px;border:0;background:transparent;color:var(--secondary-text-color);font:inherit;font-size:10px;font-weight:800;cursor:pointer}
        .tc-pressure-toggle ha-icon{--mdc-icon-size:15px}
        .tc-pressure-details{display:grid;gap:5px;margin-top:5px;padding:8px 2px 2px;border-top:1px solid color-mix(in srgb,var(--primary-text-color) 9%,transparent)}
        .tc-pressure-detail-row{display:flex;justify-content:space-between;gap:12px;font-size:10px;color:var(--secondary-text-color)}
        .tc-pressure-detail-row strong{font-weight:700;text-align:right;color:var(--secondary-text-color)}
        .tc-pressure-footnote{margin-top:2px;font-size:9.5px;line-height:1.35;color:var(--secondary-text-color);opacity:.85}
        @media(max-width:480px){
          .tc-pressure-row{grid-template-columns:22px minmax(0,1fr) auto}
          .tc-pressure-temp{display:none}
          .tc-pressure-label{font-size:11.5px}
          .tc-pressure-bar{font-size:12.5px}
        }
      `;
      root.append(style);
    }

    const detailsOpen = Boolean(this._pressureDetailsOpen);
    const section = document.createElement("section");
    section.className = "tc-pressure-plan";
    section.innerHTML = `
      <div class="tc-pressure-head">
        <div class="tc-pressure-title">CO₂-plan</div>
        ${co2 ? `<div class="tc-pressure-target">${co2} vol.</div>` : ""}
      </div>
      <div class="tc-pressure-rows">
        ${row("carbonation", "1", "Karbonering", "mdi:gauge", carbonation, "Mangler rumføler")}
        ${row("cooling", "2", "På køl", "mdi:snowflake", cooling, "Mangler måltemp.")}
        ${row("serving", "3", "Servering", "mdi:glass-cocktail", serving, "Mangler temp.")}
      </div>
      <div class="tc-pressure-action"><ha-icon icon="${actionIcon}"></ha-icon><span>${this._escape(actionText)}</span></div>
      <button class="tc-pressure-toggle" type="button">
        <span>${detailsOpen ? "Skjul detaljer" : "Vis detaljer"}</span>
        <ha-icon icon="${detailsOpen ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
      </button>
      ${detailsOpen ? `
        <div class="tc-pressure-details">
          ${detailRow("Karbonering", carbonation, "Kan ikke beregnes")}
          ${detailRow("På køl", cooling, "Kan ikke beregnes")}
          ${detailRow("Servering", serving, "Kan ikke beregnes")}
          <div class="tc-pressure-footnote">Trykkene er regulatorens ligevægtstryk. Brug flow control eller passende slangelængde til at styre hældehastigheden.</div>
        </div>` : ""}`;

    section.querySelector(".tc-pressure-toggle")?.addEventListener("click", () => {
      this._pressureDetailsOpen = !this._pressureDetailsOpen;
      this._renderPressurePlan();
    });

    const anchor = root.querySelector(".details") ?? root.querySelector(".top");
    if (anchor) anchor.insertAdjacentElement("afterend", section);
    else root.querySelector(".content")?.append(section);
  };

  p._render = function (...args) {
    const result = oldRender.apply(this, args);
    this._renderExtendedBubbles();
    this._renderPressurePlan();
    return result;
  };

  if (oldStub) Card.getStubConfig = () => ({ ...oldStub(), show_pressure_plan: true });
}

if (Editor && !Editor.__pressurePlan) {
  Editor.__pressurePlan = true;
  const p = Editor.prototype;
  const oldConfig = p.setConfig;
  const oldRender = p._render;
  const oldEmit = p._emitConfig;

  p.setConfig = function (config) {
    return oldConfig.call(this, { show_pressure_plan: true, ...config });
  };

  p._emitConfig = function (changes) {
    const presets = { full: true, serving: true, carbonation: true, compact: false, minimal: false };
    const preset = changes?.layout_preset;
    return oldEmit.call(this, {
      ...changes,
      ...(preset && preset !== "custom" && preset in presets
        ? { show_pressure_plan: presets[preset] }
        : {}),
    });
  };

  p._render = function (...args) {
    const result = oldRender.apply(this, args);
    const root = this.shadowRoot;
    if (!root || root.getElementById("show_pressure_plan")) return result;
    const section = [...root.querySelectorAll(".section")].find(
      (item) => item.querySelector(".section-title")?.textContent?.trim() === "Visning"
    );
    if (!section) return result;
    const label = document.createElement("label");
    label.className = "toggle";
    label.innerHTML = `<span>Vis CO₂-trykplan</span><input id="show_pressure_plan" type="checkbox" ${this._config.show_pressure_plan !== false ? "checked" : ""}/>`;
    const before = section.querySelector("#recipe_mode")?.closest("label");
    if (before) section.insertBefore(label, before); else section.append(label);
    label.querySelector("input")?.addEventListener("change", (event) => {
      this._emitConfig({ layout_preset: "custom", show_pressure_plan: event.target.checked });
      this._render();
    });
    return result;
  };
}

const registration = window.customCards?.find((item) => item.type === "tapcocktail-card");
if (registration) registration.description = "TapCocktail med let CO2-plan, live temperatur og bobler fra 2,0 til 4,0 vol.";
console.info("TapCocktail Card v1.6.1 - HACS review hardening active");
