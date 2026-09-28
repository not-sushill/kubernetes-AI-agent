# Application theme

The reference image informed the blue gradient header, horizontal navigation,
light workspace, white rounded cards, pale blue section headings, blue actions
and muted supporting text. Kubernetes application identity and live controls
are retained. No placeholder profile or notification actions were added.

Light is the default theme. If an existing browser preference opens in dark
mode, use the header theme toggle to choose light.

The package includes the earlier investigation history integration fix.
Stop Next.js, merge frontend into your project, then run npm ci, npm run build,
and npm run dev. Backend changes are not required.

Check at desktop and narrow browser widths:
- navigation scrolls horizontally when necessary;
- cluster selection remains accessible;
- Pods > Investigate > Open saved investigation > History still works;
- light and dark themes retain readable status indicators.

The production build and regression tests are checked during packaging.
Visual browser verification on your machine is still required.
