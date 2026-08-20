# Compatibility Runtime

This directory is a **temporary, isolated compatibility boundary**, not the frontend architecture.

The uploaded Piyush version still contains substantial imperative DOM behavior. To preserve feature parity while removing the monolithic frontend, that runtime has been split into domain controllers and is executed in original order by `RuntimeBridge.jsx`.

Do not put new screen markup here. Screen markup belongs in `src/features/**` React components.

Do not create another catch-all controller. When modifying an existing feature, prefer migrating that behavior into a feature hook/service/component and shrinking the corresponding controller.
