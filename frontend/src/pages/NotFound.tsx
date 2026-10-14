import { Link } from "react-router-dom";
import { Compass, Home } from "lucide-react";

import { EmptyState } from "../components/Spinner";

export function NotFoundPage() {
  return (
    <div className="animate-fade-up">
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="The page you are looking for does not exist. It may have moved, or the URL may be incorrect."
        action={
          <Link to="/" className="btn btn-primary">
            <Home className="h-4 w-4" aria-hidden="true" /> Back to dashboard
          </Link>
        }
      />
    </div>
  );
}