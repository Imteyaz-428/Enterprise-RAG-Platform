const activeObservers = new Set();

class Node {
  constructor(nodeType, nodeName) {
    this.nodeType = nodeType;
    this.nodeName = nodeName;
    this.childNodes = [];
    this.parentNode = null;
    this.ownerDocument = null;
  }
  get firstChild() {
    return this.childNodes[0] || null;
  }
  get textContent() {
    if (this.nodeType === 3) return this.nodeValue || "";
    return this.childNodes.map((c) => c.textContent || "").join("");
  }
  set textContent(val) {
    this.childNodes = [];
    this.appendChild(globalThis.document.createTextNode(val));
  }
  appendChild(child) {
    this.childNodes.push(child);
    child.parentNode = this;
    child.ownerDocument = this.ownerDocument || this;
    for (const obs of activeObservers) {
      try {
        obs.cb([{ type: "childList", target: this, addedNodes: [child] }], obs);
      } catch (err) {
        void err;
      }
    }
    return child;
  }
  removeChild(child) {
    const idx = this.childNodes.indexOf(child);
    if (idx !== -1) this.childNodes.splice(idx, 1);
    child.parentNode = null;
    for (const obs of activeObservers) {
      try {
        obs.cb([{ type: "childList", target: this, removedNodes: [child] }], obs);
      } catch (err) {
        void err;
      }
    }
    return child;
  }
  insertBefore(newNode, refNode) {
    const idx = this.childNodes.indexOf(refNode);
    if (idx === -1) return this.appendChild(newNode);
    this.childNodes.splice(idx, 0, newNode);
    newNode.parentNode = this;
    newNode.ownerDocument = this.ownerDocument || this;
    for (const obs of activeObservers) {
      try {
        obs.cb([{ type: "childList", target: this, addedNodes: [newNode] }], obs);
      } catch (err) {
        void err;
      }
    }
    return newNode;
  }
  contains(child) {
    if (child === this) return true;
    for (const c of this.childNodes) {
      if (c.contains && c.contains(child)) return true;
    }
    return false;
  }
  cloneNode(deep = false) {
    const clone = new this.constructor(this.nodeName);
    clone.nodeValue = this.nodeValue;
    if (deep) {
      for (const c of this.childNodes) {
        clone.appendChild(c.cloneNode(true));
      }
    }
    return clone;
  }
}

class Text extends Node {
  constructor(text = "") {
    super(3, "#text");
    this.nodeValue = String(text);
  }
  get data() {
    return this.nodeValue;
  }
  set data(v) {
    this.nodeValue = String(v);
  }
}

class Comment extends Node {
  constructor(text = "") {
    super(8, "#comment");
    this.nodeValue = String(text);
  }
}

class HTMLElement extends Node {
  constructor(name = "div") {
    super(1, String(name).toUpperCase());
    this.tagName = String(name).toUpperCase();
    this.namespaceURI = "http://www.w3.org/1999/xhtml";
    this.attributes = {};
    this.style = {};
  }
  get outerHTML() {
    const tag = this.tagName.toLowerCase();
    const attrs = Object.entries(this.attributes)
      .map(([k, v]) => ` ${k}="${v}"`)
      .join("");
    return `<${tag}${attrs}>${this.innerHTML}</${tag}>`;
  }
  get innerHTML() {
    return this.childNodes
      .map((c) => (c.nodeType === 1 ? c.outerHTML : c.textContent || ""))
      .join("");
  }
  set innerHTML(html) {
    this.childNodes = [];
    if (html) {
      this.appendChild(globalThis.document.createTextNode(html));
    }
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
  }
  getAttribute(k) {
    return this.attributes[k] || null;
  }
  removeAttribute(k) {
    delete this.attributes[k];
  }
  hasAttribute(k) {
    return k in this.attributes;
  }
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() {
    return true;
  }
  matches(sel) {
    if (sel === "*") return true;
    if (sel.toLowerCase() === this.tagName.toLowerCase()) return true;
    if (sel.startsWith("[") && sel.endsWith("]")) {
      const attr = sel.slice(1, -1);
      return attr in this.attributes;
    }
    return false;
  }
  querySelectorAll(sel) {
    const res = [];
    const check = (node) => {
      for (const c of node.childNodes) {
        if (c.nodeType === 1) {
          if (c.matches(sel)) res.push(c);
          check(c);
        }
      }
    };
    check(this);
    return res;
  }
  querySelector(sel) {
    return this.querySelectorAll(sel)[0] || null;
  }
}

class HTMLDivElement extends HTMLElement {}
class HTMLInputElement extends HTMLElement {}
class HTMLIFrameElement extends HTMLElement {}
class HTMLParagraphElement extends HTMLElement {}
class HTMLHeadingElement extends HTMLElement {}
class HTMLButtonElement extends HTMLElement {}
class HTMLAnchorElement extends HTMLElement {}
class HTMLSpanElement extends HTMLElement {}
class HTMLFormElement extends HTMLElement {}
class SVGSVGElement extends HTMLElement {}
class SVGPathElement extends HTMLElement {}

function createHTMLElement(tag) {
  const t = String(tag).toLowerCase();
  let el;
  switch (t) {
    case "input":
      el = new HTMLInputElement("input");
      break;
    case "iframe":
      el = new HTMLIFrameElement("iframe");
      break;
    case "p":
      el = new HTMLParagraphElement("p");
      break;
    case "h1":
    case "h2":
    case "h3":
    case "h4":
    case "h5":
    case "h6":
      el = new HTMLHeadingElement(t);
      break;
    case "button":
      el = new HTMLButtonElement("button");
      break;
    case "a":
      el = new HTMLAnchorElement("a");
      break;
    case "span":
      el = new HTMLSpanElement("span");
      break;
    case "form":
      el = new HTMLFormElement("form");
      break;
    case "svg":
      el = new SVGSVGElement("svg");
      break;
    case "path":
      el = new SVGPathElement("path");
      break;
    default:
      el = new HTMLDivElement(t);
      break;
  }
  el.ownerDocument = globalThis.document;
  return el;
}

class Document extends Node {
  constructor() {
    super(9, "#document");
    this.head = new HTMLDivElement("head");
    this.head.ownerDocument = this;
    this.body = new HTMLDivElement("body");
    this.body.ownerDocument = this;
    this.documentElement = new HTMLDivElement("html");
    this.documentElement.ownerDocument = this;
    this.activeElement = null;
    this.defaultView = globalThis;
  }
  createElement(tag) {
    return createHTMLElement(tag);
  }
  createElementNS(ns, tag) {
    const el = this.createElement(tag);
    el.namespaceURI = ns;
    return el;
  }
  createComment(t) {
    const node = new Comment(t);
    node.ownerDocument = this;
    return node;
  }
  createTextNode(t) {
    const node = new Text(t);
    node.ownerDocument = this;
    return node;
  }
  querySelector(sel) {
    return this.body.querySelector(sel);
  }
  querySelectorAll(sel) {
    return this.body.querySelectorAll(sel);
  }
  addEventListener() {}
  removeEventListener() {}
}

class MutationObserver {
  constructor(cb) {
    this.cb = cb;
  }
  observe() {
    activeObservers.add(this);
  }
  disconnect() {
    activeObservers.delete(this);
  }
  takeRecords() {
    return [];
  }
}

if (!globalThis.document) {
  globalThis.Node = Node;
  globalThis.Text = Text;
  globalThis.Comment = Comment;
  globalThis.Element = HTMLElement;
  globalThis.HTMLElement = HTMLElement;
  globalThis.HTMLDivElement = HTMLDivElement;
  globalThis.HTMLInputElement = HTMLInputElement;
  globalThis.HTMLIFrameElement = HTMLIFrameElement;
  globalThis.HTMLParagraphElement = HTMLParagraphElement;
  globalThis.HTMLHeadingElement = HTMLHeadingElement;
  globalThis.HTMLButtonElement = HTMLButtonElement;
  globalThis.HTMLAnchorElement = HTMLAnchorElement;
  globalThis.HTMLSpanElement = HTMLSpanElement;
  globalThis.HTMLFormElement = HTMLFormElement;
  globalThis.SVGSVGElement = SVGSVGElement;
  globalThis.SVGPathElement = SVGPathElement;
  globalThis.Document = Document;
  globalThis.MutationObserver = MutationObserver;

  const mockDoc = new Document();
  const location = {
    href: "http://localhost:5173/",
    origin: "http://localhost:5173",
    protocol: "http:",
    host: "localhost:5173",
    hostname: "localhost",
    port: "5173",
    pathname: "/",
    search: "",
    hash: "",
    reload: () => {},
    replace: () => {},
    assign: () => {},
  };
  globalThis.location = location;
  globalThis.document = mockDoc;
  globalThis.window = globalThis;
  globalThis.window.location = location;
  globalThis.window.document = mockDoc;
  globalThis.window.addEventListener = () => {};
  globalThis.window.removeEventListener = () => {};
}

// LocalStorage mock
const storage = {};
globalThis.localStorage = {
  getItem: (k) => storage[k] || null,
  setItem: (k, v) => {
    storage[k] = String(v);
  },
  removeItem: (k) => {
    delete storage[k];
  },
  clear: () => {
    for (const k in storage) delete storage[k];
  },
};
