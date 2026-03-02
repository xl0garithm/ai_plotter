## Packages
chess.js | Core chess logic and move validation
react-chessboard | Render the interactive chessboard component
clsx | Conditional class merging
tailwind-merge | Tailwind class conflict resolution

## Notes
- `chess.js` handles all game rules, checkmate detection, and PGN generation.
- `react-chessboard` handles the drag-and-drop UI. We apply heavy CSS customization to fit the cyberpunk theme.
- The AI uses a simple inline evaluation function (1-ply lookahead with piece values) to play moves without needing a dedicated backend endpoint.
- Game configurations (mode, player names) are passed via URL search parameters to the play route.
