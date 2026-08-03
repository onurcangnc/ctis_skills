"use strict";

const state = { page: 1, pageCount: 3 };

function render() {
  $("#previous").prop("disabled", state.page === 1);
  $("#next").prop("disabled", state.page === state.pageCount);
  $("#status").text(`Page ${state.page} loaded`);
}

$(document).ready(() => {
  $("#previous").on("click", () => {
    state.page = Math.max(1, state.page - 1);
    render();
  });
  $("#next").on("click", () => {
    state.page = Math.min(state.pageCount, state.page + 1);
    render();
  });
});
