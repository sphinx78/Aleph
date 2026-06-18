import React, { useState } from 'react';
import GlobeLanding from './components/GlobeLanding';
import DashboardMain from './components/DashboardMain';

function App() {
  const [isEntered, setIsEntered] = useState(false);

  return (
    <>
      {!isEntered ? (
        <GlobeLanding onEnter={() => setIsEntered(true)} />
      ) : (
        <div className="animate-fade-in">
          <DashboardMain />
        </div>
      )}
    </>
  );
}

export default App;
