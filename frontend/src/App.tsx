import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Detection from './pages/Detection';
import LiveCamera from './pages/LiveCamera';
import Analytics from './pages/Analytics';
import Reports from './pages/Reports';
import ViolationLogs from './pages/ViolationLogs';
import Evidence from './pages/Evidence';
import Settings from './pages/Settings';
import Review from './pages/Review';
import Insights from './pages/Insights';
import Metrics from './pages/Metrics';
import { ErrorBoundary } from './components/common/ErrorBoundary';

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="live" element={<LiveCamera />} />
          <Route path="detection" element={<Detection />} />
          <Route path="video" element={<Detection />} />
          <Route path="logs" element={<ViolationLogs />} />
          <Route path="reports" element={<Reports />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="evidence" element={<Evidence />} />
          <Route path="settings" element={<Settings />} />
          <Route path="review" element={<Review />} />
          <Route path="insights" element={<Insights />} />
          <Route path="metrics" element={<Metrics />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}
