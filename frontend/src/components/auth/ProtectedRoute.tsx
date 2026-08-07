import { Navigate } from 'react-router-dom';
import { isAuthenticated } from '@/api/client';

interface Props {
	children: React.ReactNode;
}

/**
 * Route guard that checks for authentication.
 *
 * Requires a valid JWT token (auth_token in localStorage) to access.
 * Redirects to /setup if not authenticated.
 */
export const ProtectedRoute = ({ children }: Props) => {
	// JWT authenticated
	if (isAuthenticated()) {
		return <>{children}</>;
	}

	// Not authenticated — redirect to setup
	return <Navigate to="/setup" replace />;
};