<template>
  <div class="custom-select" ref="wrapper" :style="{ width: width }">
    <div class="input-group">
      <input
        ref="input"
        type="text"
        class="control h-lg"
        :value="modelValue"
        :placeholder="placeholder"
        @input="onInput"
        @focus="showOptions"
        @blur="onBlur"
        @keydown.down.prevent="highlightNext"
        @keydown.up.prevent="highlightPrev"
        @keydown.enter.prevent="selectHighlighted"
        @keydown.esc="hideOptions"
        style="flex:1;min-width:0;border-radius:4px 0 0 4px;"
      />
      <button
        class="btn btn-default dropdown-btn"
        @mousedown.prevent="toggleOptions"
        type="button"
      >
        ▼
      </button>
    </div>
    <ul v-show="show" class="options-list" ref="list">
      <li
        v-for="(opt, idx) in options"
        :key="opt"
        :class="{ active: highlightedIndex === idx }"
        @mousedown.prevent="selectOption(opt)"
        @mouseenter="highlightedIndex = idx"
      >
        {{ opt }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'CustomSelect',
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    options: {
      type: Array,
      required: true
    },
    placeholder: {
      type: String,
      default: ''
    },
    width: {
      type: String,
      default: '140px'
    }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      show: false,
      highlightedIndex: -1,
    };
  },
  watch: {
    modelValue() {
      this.highlightedIndex = -1;
    }
  },
  methods: {
    onInput(e) {
      this.$emit('update:modelValue', e.target.value);
    },
    showOptions() {
      this.show = true;
      this.highlightedIndex = -1;
    },
    hideOptions() {
      this.show = false;
      this.highlightedIndex = -1;
    },
    toggleOptions() {
      this.show = !this.show;
      if (this.show) this.highlightedIndex = -1;
    },
    selectOption(opt) {
      this.$emit('update:modelValue', opt);
      this.hideOptions();
      this.$refs.input.focus();
    },
    highlightNext() {
      if (!this.show) this.show = true;
      if (this.highlightedIndex < this.options.length - 1) {
        this.highlightedIndex++;
        this.scrollToHighlight();
      }
    },
    highlightPrev() {
      if (this.highlightedIndex > 0) {
        this.highlightedIndex--;
        this.scrollToHighlight();
      }
    },
    selectHighlighted() {
      if (this.highlightedIndex >= 0) {
        this.selectOption(this.options[this.highlightedIndex]);
      }
    },
    scrollToHighlight() {
      const list = this.$refs.list;
      const items = list.querySelectorAll('li');
      if (items[this.highlightedIndex]) {
        items[this.highlightedIndex].scrollIntoView({ block: 'nearest' });
      }
    },
    onBlur(e) {
      setTimeout(() => {
        this.hideOptions();
      }, 150);
    }
  }
};
</script>

<style scoped>
.custom-select {
  position: relative;
  display: inline-block;
  vertical-align: middle;
}
.input-group {
  display: flex;
  align-items: center;
  width: 100%;
}
.input-group .control {
  flex: 1;
  min-width: 0;
}
.input-group .dropdown-btn {
  flex-shrink: 0;
  border: 1px solid #d9d9d9;
  border-left: none;
  border-radius: 0 4px 4px 0;
  padding: 0 8px;
  height: 32px;
  background: white;
  cursor: pointer;
  color: #333;
  font-size: 12px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.input-group .dropdown-btn:hover {
  background: #f0f0f0;
}
.options-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 150px;
  overflow-y: auto;
  background: white;
  border: 1px solid #d9d9d9;
  border-top: none;
  border-radius: 0 0 4px 4px;
  list-style: none;
  padding: 0;
  margin: 0;
  z-index: 9999;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.options-list li {
  padding: 4px 10px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.options-list li:hover,
.options-list li.active {
  background: #e6f7ff;
}
</style>