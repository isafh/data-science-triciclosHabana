/* Informe Triciclos La Habana — interacción del sitio */
(function () {
  "use strict";

  /* ------------------------------------------------ navegación activa */
  var enlaces = Array.prototype.slice.call(document.querySelectorAll(".barra__nav a"));
  var secciones = enlaces
    .map(function (a) { return document.querySelector(a.getAttribute("href")); })
    .filter(Boolean);

  if ("IntersectionObserver" in window && secciones.length) {
    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (!e.isIntersecting) return;
        enlaces.forEach(function (a) {
          a.classList.toggle("activo", a.getAttribute("href") === "#" + e.target.id);
        });
      });
    }, { rootMargin: "-45% 0px -50% 0px", threshold: 0 });
    secciones.forEach(function (s) { observador.observe(s); });
  }

  /* ------------------------------------------------ tabla de datos */
  var tabla = document.getElementById("tabla-datos");
  if (tabla) {
    var cuerpo = tabla.tBodies[0];
    var filas = Array.prototype.slice.call(cuerpo.rows);
    var filtroFuente = document.getElementById("f-fuente");
    var filtroTipo = document.getElementById("f-tipo");
    var busqueda = document.getElementById("f-buscar");
    var contador = document.getElementById("contador-datos");

    var aplicar = function () {
      var f = filtroFuente ? filtroFuente.value : "";
      var t = filtroTipo ? filtroTipo.value : "";
      var q = busqueda ? busqueda.value.trim().toLowerCase() : "";
      var visibles = 0;
      filas.forEach(function (tr) {
        var okF = !f || tr.dataset.fuente === f;
        var okT = !t || tr.dataset.tipo === t;
        var okQ = !q || tr.textContent.toLowerCase().indexOf(q) !== -1;
        var visible = okF && okT && okQ;
        tr.hidden = !visible;
        if (visible) visibles++;
      });
      if (contador) contador.textContent = visibles + " de " + filas.length + " registros visibles";
    };

    [filtroFuente, filtroTipo, busqueda].forEach(function (el) {
      if (el) el.addEventListener("input", aplicar);
      if (el) el.addEventListener("change", aplicar);
    });
    aplicar();

    var encabezados = Array.prototype.slice.call(tabla.tHead.rows[0].cells);
    var orden = { col: -1, dir: 1 };
    encabezados.forEach(function (th, idx) {
      th.addEventListener("click", function () {
        var dir = (orden.col === idx && orden.dir === 1) ? -1 : 1;
        orden = { col: idx, dir: dir };
        encabezados.forEach(function (h) { h.removeAttribute("data-orden"); });
        th.setAttribute("data-orden", dir === 1 ? "asc" : "desc");
        var num = th.dataset.tipo === "num";
        filas.sort(function (a, b) {
          var va = a.cells[idx].dataset.valor;
          var vb = b.cells[idx].dataset.valor;
          if (va === undefined) va = a.cells[idx].textContent.trim();
          if (vb === undefined) vb = b.cells[idx].textContent.trim();
          if (num) return (parseFloat(va) - parseFloat(vb)) * dir;
          return String(va).localeCompare(String(vb), "es") * dir;
        });
        filas.forEach(function (tr) { cuerpo.appendChild(tr); });
      });
    });
  }

  /* ------------------------------------------------ calculadora de rentabilidad */
  var calc = document.getElementById("calc");
  if (!calc) return;

  var PRECIOS = { electrico: 4825, hibrido: 4625.5, combustion: 5875, solar: 5500 };
  var SALARIO_CUP = 7442.2;
  var MESES_BARRA = 60;

  var $ = function (id) { return document.getElementById(id); };
  var entradas = ["tipo", "tarifa", "pasajeros", "dias", "margen", "fx"];

  var nf0 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" });
  var nf1 = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1, useGrouping: "always" });
  var nf2 = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: "always" });

  function calcular() {
    var tipo = $("tipo").value;
    var tarifa = parseFloat($("tarifa").value) || 0;
    var pasajeros = parseFloat($("pasajeros").value) || 0;
    var dias = parseFloat($("dias").value) || 0;
    var margen = (parseFloat($("margen").value) || 0) / 100;
    var fx = parseFloat($("fx").value) || 1;
    var precio = PRECIOS[tipo] || PRECIOS.electrico;

    var bruto = tarifa * pasajeros * dias;
    var costos = bruto * margen;
    var neto = bruto - costos;
    var netoUsd = neto / fx;
    var meses = netoUsd > 0 ? precio / netoUsd : Infinity;
    var pasajeros12 = 0;
    if (tarifa > 0 && dias > 0 && (1 - margen) > 0) {
      pasajeros12 = (precio / 12) * fx / (tarifa * dias * (1 - margen));
    }

    $("r-precio").textContent = "$" + nf0.format(precio);
    $("r-bruto").textContent = nf0.format(bruto) + " CUP";
    $("r-costos").textContent = "−" + nf0.format(costos) + " CUP";
    $("r-neto").textContent = nf0.format(neto) + " CUP · $" + nf1.format(netoUsd);
    $("r-pasajeros12").textContent = isFinite(pasajeros12) ? nf1.format(pasajeros12) : "—";
    $("r-salarios").textContent = neto > 0 ? nf1.format(neto / SALARIO_CUP) + " salarios/mes" : "—";

    if (isFinite(meses)) {
      $("r-meses").textContent = nf1.format(meses);
      $("r-anios").textContent = nf1.format(meses / 12) + " años";
      var pct = Math.max(2, Math.min(100, (meses / MESES_BARRA) * 100));
      $("r-barra").style.width = pct + "%";
      $("r-barra-nota").textContent = meses <= 12
        ? "Recuperación en menos de un año"
        : (meses <= MESES_BARRA
          ? "Dentro de la ventana de 5 años"
          : "Supera los 5 años de operación");
    } else {
      $("r-meses").textContent = "∞";
      $("r-anios").textContent = "no se recupera";
      $("r-barra").style.width = "100%";
      $("r-barra-nota").textContent = "Con estos supuestos el ingreso neto es cero";
    }
  }

  entradas.forEach(function (id) {
    var el = $(id);
    if (!el) return;
    el.addEventListener("input", function () {
      var salida = el.parentElement.querySelector("output");
      if (salida) {
        salida.textContent = id === "fx"
          ? nf0.format(parseFloat(el.value) || 0)
          : (id === "margen" ? el.value + " %" : el.value);
      }
      calcular();
    });
    el.addEventListener("change", calcular);
  });

  var reiniciar = document.getElementById("calc-reset");
  if (reiniciar) {
    reiniciar.addEventListener("click", function () {
      $("tipo").value = "electrico";
      $("tarifa").value = 450;
      $("pasajeros").value = 30;
      $("dias").value = 26;
      $("margen").value = 15;
      $("fx").value = 900;
      entradas.forEach(function (id) {
        var el = $(id);
        var salida = el && el.parentElement.querySelector("output");
        if (salida) {
          salida.textContent = id === "fx" ? nf0.format(parseFloat(el.value))
            : (id === "margen" ? el.value + " %" : el.value);
        }
      });
      calcular();
    });
  }

  calcular();
})();
