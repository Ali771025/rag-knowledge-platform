import { RouterProvider } from "react-router-dom";
import { appRouter } from "./app/routes";
import { ErrorBoundary } from "@/components/ui";

export default function App() {
  return (
    <ErrorBoundary>
      <RouterProvider router={appRouter} />
    </ErrorBoundary>
  );
}
