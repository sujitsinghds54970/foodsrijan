/// <reference types="react-scripts" />

declare module '*.css' {
  const content: { [className: string]: string };
  export default content;
}

declare module '*.scss' {
  const content: { [className: string]: string };
  export default content;
}

declare module '@ag-grid-community/styles/ag-grid.css';
declare module '@ag-grid-community/styles/ag-theme-alpine.css';
