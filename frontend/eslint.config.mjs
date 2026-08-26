// Guardián de las Rules of Hooks: un hook tras un return temprano tumba TODA
// la app en blanco en runtime (pasó con ClientPlanPanel el 26-08-2026 — el
// coach veía la pestaña Planificación en blanco). `npm run lint:hooks` debe
// estar en verde antes de fusionar cualquier cambio de frontend.
import reactHooks from "eslint-plugin-react-hooks";
import tsParser from "@typescript-eslint/parser";

export default [
  {
    files: ["src/**/*.ts", "src/**/*.tsx"],
    languageOptions: { parser: tsParser, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { "react-hooks": reactHooks },
    rules: { "react-hooks/rules-of-hooks": "error" },
  },
];
