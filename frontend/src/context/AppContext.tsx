import React, { createContext, useContext, useReducer, ReactNode } from 'react';

interface AppState {
  sidebarCollapsed: boolean;
  theme: 'dark' | 'cyberpunk';
  notifications: number;
}

type Action =
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_THEME'; payload: 'dark' | 'cyberpunk' }
  | { type: 'SET_NOTIFICATIONS'; payload: number };

const initialState: AppState = {
  sidebarCollapsed: false,
  theme: 'dark',
  notifications: 0,
};

function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    case 'SET_THEME':
      return { ...state, theme: action.payload };
    case 'SET_NOTIFICATIONS':
      return { ...state, notifications: action.payload };
    default:
      return state;
  }
}

const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<Action>;
} | null>(null);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppState = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppState must be used within AppProvider');
  return ctx;
};
