export function openDetail(title, content) {
  const dialog = document.getElementById('details');
  document.getElementById('detail-title').textContent = title;
  document.getElementById('detail-body').replaceChildren(content);
  if (!dialog.open) dialog.showModal();
}
