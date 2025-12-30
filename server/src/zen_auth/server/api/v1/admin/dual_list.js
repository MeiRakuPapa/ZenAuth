class DualList {
  constructor(selectEl, options = {}) {
    this.select = selectEl;
    this.select.style.display = "none";

    this.size = this.select.size > 1 ? this.select.size : 8;
    this.items = [...this.select.options].map((opt) => ({
      value: opt.value,
      label: opt.textContent,
      selected: opt.selected,
    }));

    // Default labels with fallback to options
    this.labels = {
      available: options.availableLabel || "Available",
      selected: options.selectedLabel || "Selected",
      ...options.labels,
    };

    this.wrapper = document.createElement("div");
    this.wrapper.className = "dl-container";
    this.select.after(this.wrapper);

    this.buildUI();
    this.renderLists();
    this.applyListSize(this.available);
    this.applyListSize(this.selected);

    this.bindEvents();
    this.enableDnD();

    this.lastClicked = null;
    this.syncBack();
  }

  static setup(selector) {
    try {
      new DualList(document.querySelector(selector));
    } catch (e) {
      console.error(selector, e);
    }
  }

  buildUI() {
    this.wrapper.innerHTML = `
      <div class="dl-column">
        <div class="dl-inner-label">${this.labels.available}</div>
        <div class="dl-list dl-available" data-size="${this.size}"></div>
      </div>

      <div class="dl-column">
        <div class="dl-btn dl-to-selected">▶</div>
        <div class="dl-btn dl-to-available">◀</div>
      </div>

      <div class="dl-column">
        <div class="dl-inner-label">${this.labels.selected}</div>
        <div class="dl-list dl-selected" data-size="${this.size}"></div>
      </div>
    `;

    this.available = this.wrapper.querySelector(".dl-available");
    this.selected = this.wrapper.querySelector(".dl-selected");
    this.toSel = this.wrapper.querySelector(".dl-to-selected");
    this.toAva = this.wrapper.querySelector(".dl-to-available");
  }

  applyListSize(list) {
    const size = Number(list.dataset.size) || this.size;
    const tmp = document.createElement("div");
    tmp.className = "dl-item";
    tmp.textContent = "X";
    tmp.style.visibility = "hidden";
    list.appendChild(tmp);
    const rowHeight = tmp.getBoundingClientRect().height;
    list.removeChild(tmp);

    list.style.height = `${rowHeight * size}px`;
    list.style.maxHeight = `${rowHeight * size}px`;
  }

  renderLists() {
    this.available.innerHTML = "";
    this.selected.innerHTML = "";

    for (const it of this.items) {
      const div = document.createElement("div");
      div.className = "dl-item";
      div.textContent = it.label;
      div.dataset.value = it.value;

      if (it.selected) this.selected.appendChild(div);
      else this.available.appendChild(div);

      this.enableSelect(div);
    }
  }

  enableSelect(div) {
    div.addEventListener("click", (e) => {
      const parent = div.parentElement;
      const items = [...parent.children];
      const index = items.indexOf(div);

      const other = parent === this.available ? this.selected : this.available;
      [...other.children].forEach((item) => item.classList.remove("selected"));

      if (e.ctrlKey || e.metaKey) {
        div.classList.toggle("selected");
        this.lastClicked = div;
        return;
      }

      if (
        e.shiftKey &&
        this.lastClicked &&
        this.lastClicked.parentElement === parent
      ) {
        const lastIndex = items.indexOf(this.lastClicked);
        const [start, end] = [
          Math.min(index, lastIndex),
          Math.max(index, lastIndex),
        ];
        items.forEach((item, i) => {
          if (i >= start && i <= end) item.classList.add("selected");
        });
        return;
      }

      items.forEach((item) => item.classList.remove("selected"));
      div.classList.add("selected");
      this.lastClicked = div;
    });
  }

  bindEvents() {
    this.toSel.onclick = () => this.move(this.available, this.selected);
    this.toAva.onclick = () => this.move(this.selected, this.available);
  }

  move(from, to) {
    const selectedItems = [...from.children].filter((d) =>
      d.classList.contains("selected")
    );
    if (selectedItems.length === 0) return;

    selectedItems.forEach((div) => {
      div.classList.remove("selected");
      to.appendChild(div);
    });

    this.updateItems();
    this.syncBack();
  }

  updateItems() {
    const sel = [...this.selected.children].map((d) => d.dataset.value);
    this.items.forEach((it) => {
      it.selected = sel.includes(it.value);
    });
  }

  syncBack() {
    [...this.select.options].forEach((opt) => {
      const it = this.items.find((i) => i.value === opt.value);
      opt.selected = it.selected;
    });
  }

  enableDnD() {
    const makeDraggable = (list) => {
      [...list.children].forEach((div) => {
        div.draggable = true;

        div.addEventListener("dragstart", (e) => {
          const selectedValues = [...list.children]
            .filter((d) => d.classList.contains("selected"))
            .map((d) => d.dataset.value);

          if (!selectedValues.length) div.classList.add("selected");

          e.dataTransfer.setData("text/json", JSON.stringify(selectedValues));
        });
      });
    };

    const makeDroppable = (list) => {
      list.addEventListener("dragover", (e) => e.preventDefault());

      list.addEventListener("drop", (e) => {
        e.preventDefault();
        let values = JSON.parse(e.dataTransfer.getData("text/json"));
        values.forEach((v) => {
          const div = this.wrapper.querySelector(`.dl-item[data-value="${v}"]`);
          if (div) list.appendChild(div);
        });

        this.updateItems();
        this.syncBack();

        [...this.available.children].forEach((d) =>
          d.classList.remove("selected")
        );
        [...this.selected.children].forEach((d) =>
          d.classList.remove("selected")
        );

        makeDraggable(this.available);
        makeDraggable(this.selected);
      });
    };

    makeDraggable(this.available);
    makeDraggable(this.selected);
    makeDroppable(this.available);
    makeDroppable(this.selected);
  }

  getSelected() {
    return [...this.select.options]
      .filter((e) => e.selected)
      .map((e) => e.value);
  }

  setSelected(values) {
    const set = new Set(values);

    [...this.select.options].forEach((opt) => {
      opt.selected = set.has(opt.value);
    });

    this.items.forEach((it) => {
      it.selected = set.has(it.value);
    });

    this.renderLists();

    this.applyListSize(this.available);
    this.applyListSize(this.selected);

    this.enableDnD();
  }
}
