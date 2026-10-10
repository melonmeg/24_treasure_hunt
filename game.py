import pygame
import random

TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY, SPIKE, FLAME = 0, 1, 2, 3, 4, 5
TRAPS = (SPIKE, FLAME)
FLAME_PERIOD, FLAME_ON = 120, 60   # frames per cycle / frames the flame is lit
NUM_TRAPS = 8
GUARD_SPEED = 2
MAP_TILE = 6
SPEED = 3

def reachable(grid, start, goals):
    """BFS over non-wall, non-trap tiles; True if every goal can be reached from start."""
    seen, queue = {start}, [start]
    while queue:
        c, r = queue.pop()
        for nc, nr in ((c+1,r),(c-1,r),(c,r+1),(c,r-1)):
            if (nc, nr) not in seen and 0<=nr<ROWS and 0<=nc<COLS \
               and grid[nr][nc] != WALL and grid[nr][nc] not in TRAPS:
                seen.add((nc, nr))
                queue.append((nc, nr))
    return all(g in seen for g in goals)

def place_traps(grid, rooms):
    """Scatter traps on floor tiles outside the start and chest rooms, never cutting off the key or chest."""
    if len(rooms) < 3:
        return
    start = (rooms[0].centerx, rooms[0].centery)
    goals = [(rooms[-1].centerx, rooms[-1].centery), (rooms[-2].centerx, rooms[-2].centery)]
    candidates = [(c, r) for r in range(ROWS) for c in range(COLS)
                  if grid[r][c] == FLOOR and not rooms[0].collidepoint(c, r)
                  and not rooms[-1].collidepoint(c, r)]
    random.shuffle(candidates)
    placed = 0
    for c, r in candidates:
        if placed >= NUM_TRAPS:
            break
        grid[r][c] = SPIKE if placed % 2 == 0 else FLAME
        if reachable(grid, start, goals):
            placed += 1
        else:
            grid[r][c] = FLOOR

def generate_world():
    grid = [[WALL]*COLS for _ in range(ROWS)]
    rooms = []
    for _ in range(8):
        w = random.randint(3,6)
        h = random.randint(3,5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)
        overlap = any(room.inflate(2,2).colliderect(r) for r in rooms)
        if not overlap:
            rooms.append(room)
            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery
        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            cx += 1 if bx > cx else -1
        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            cy += 1 if by > cy else -1

    if len(rooms) >= 2:
        cr, ck = rooms[-1], rooms[-2]
        grid[cr.centery][cr.centerx] = CHEST
        grid[ck.centery][ck.centerx] = KEY
        place_traps(grid, rooms)

    start = rooms[0] if rooms else None
    chest_room = rooms[-1] if len(rooms) >= 2 else None
    return grid, start, chest_room

COLORS = {
    WALL: (60,50,70),
    FLOOR: (200,190,170),
    CHEST: (200,160,30),
    KEY: (220,220,60),
    SPIKE: (200,190,170),
    FLAME: (200,190,170),
}

class Guard:
    """Patrols horizontally between two points, one row above the chest."""
    def __init__(self, room):
        y = (room.centery - 1) * TILE + 6
        self.left = room.left * TILE + 6
        self.right = (room.right - 1) * TILE + 6
        self.rect = pygame.Rect(self.left, y, 28, 28)
        self.dir = 1

    def update(self):
        self.rect.x += GUARD_SPEED * self.dir
        if self.rect.x >= self.right:
            self.rect.x, self.dir = self.right, -1
        elif self.rect.x <= self.left:
            self.rect.x, self.dir = self.left, 1

    def draw(self, screen):
        pygame.draw.rect(screen, (200,40,40), self.rect, border_radius=6)
        pygame.draw.circle(screen, (255,255,255), (self.rect.centerx-6, self.rect.centery-3), 3)
        pygame.draw.circle(screen, (255,255,255), (self.rect.centerx+6, self.rect.centery-3), 3)

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60,120,220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx=dy=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx=-SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy=-SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy=SPEED
        self._try_move(dx,0,grid,rows,cols)
        self._try_move(0,dy,grid,rows,cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx,dy)
        for px,py in [(new.left,new.top),(new.right-1,new.top),(new.left,new.bottom-1),(new.right-1,new.bottom-1)]:
            c,r=px//TILE,py//TILE
            if not(0<=r<rows and 0<=c<cols) or grid[r][c]==WALL:
                return
        self.rect=new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)
        if self.has_key:
            pygame.draw.circle(screen, (220,220,60), (self.rect.right-6, self.rect.top+6), 5)


WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)
        self.reset()

    def reset(self):
        self.grid, start, chest_room = generate_world()
        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6
        self.start_pos = (sx, sy)
        self.player = Player(sx, sy)
        self.guard = Guard(chest_room) if chest_room else None
        self.frame = 0
        self.flash = 0
        self.won = False
        self.status = "Find the KEY, then the CHEST!"

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.reset()
        return True

    def send_to_start(self, message):
        self.player.rect.topleft = self.start_pos
        self.status = message
        self.flash = 30

    def flame_lit(self):
        return self.frame % FLAME_PERIOD < FLAME_ON

    def update(self):
        self.frame += 1
        if self.flash: self.flash -= 1
        if self.won: return
        if self.guard:
            self.guard.update()
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.grid, ROWS, COLS)
        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE
        if 0<=pr<ROWS and 0<=pc<COLS:
            cell = self.grid[pr][pc]
            if cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"
            elif cell == CHEST and self.player.has_key:
                self.won = True
                self.status = "Treasure found!"
            elif cell == SPIKE:
                self.send_to_start("Spike trap! Back to start.")
            elif cell == FLAME and self.flame_lit():
                self.send_to_start("Flame trap! Back to start.")
        if self.guard and not self.won and self.player.rect.colliderect(self.guard.rect):
            self.send_to_start("Caught by the guard! Back to start.")

    def draw(self):
        self.screen.fill((30,25,40))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                rect = pygame.Rect(c*TILE, r*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, COLORS[cell], rect)
                if cell == KEY:
                    pygame.draw.circle(self.screen, (255,240,60),(c*TILE+TILE//2, r*TILE+TILE//2),10)
                elif cell == CHEST:
                    pygame.draw.rect(self.screen,(180,120,20),rect.inflate(-12,-12),border_radius=4)
                elif cell == SPIKE:
                    for i in range(3):
                        x = rect.x + 6 + i*10
                        pygame.draw.polygon(self.screen, (110,110,120), [(x, rect.bottom-6), (x+5, rect.top+8), (x+10, rect.bottom-6)])
                elif cell == FLAME:
                    if self.flame_lit():
                        pygame.draw.circle(self.screen, (240,100,20), rect.center, 14)
                        pygame.draw.circle(self.screen, (255,220,60), rect.center, 7)
                    else:
                        pygame.draw.circle(self.screen, (90,60,50), rect.center, 12, 3)
        if self.guard:
            self.guard.draw(self.screen)
        self.player.draw(self.screen)
        if self.flash:
            ov = pygame.Surface((WIDTH, ROWS*TILE), pygame.SRCALPHA)
            ov.fill((220,30,30,int(120*self.flash/30)))
            self.screen.blit(ov,(0,0))
        self.draw_minimap()
        hud = pygame.Rect(0,ROWS*TILE,WIDTH,50)
        pygame.draw.rect(self.screen,(20,20,35),hud)
        st = self.font.render(self.status+"  |  R=Restart", True, (200,200,200))
        self.screen.blit(st,(8,ROWS*TILE+13))
        self.draw_inventory(hud)
        if self.won:
            ov=pygame.Surface((WIDTH,ROWS*TILE),pygame.SRCALPHA)
            ov.fill((0,0,0,140))
            self.screen.blit(ov,(0,0))
            msg=self.big_font.render("TREASURE FOUND!", True,(220,180,30))
            sub=self.font.render("Press R to Play Again",True,(180,180,180))
            self.screen.blit(msg,(WIDTH//2-msg.get_width()//2,ROWS*TILE//2-30))
            self.screen.blit(sub,(WIDTH//2-sub.get_width()//2,ROWS*TILE//2+20))
        pygame.display.flip()

    def draw_inventory(self, hud):
        slot = pygame.Rect(WIDTH-50, hud.y+5, 40, 40)
        pygame.draw.rect(self.screen, (45,45,65), slot, border_radius=6)
        pygame.draw.rect(self.screen, (140,140,170), slot, 2, border_radius=6)
        if self.player.has_key:
            cx, cy = slot.centerx-6, slot.centery
            pygame.draw.circle(self.screen, (255,240,60), (cx, cy), 7, 3)
            pygame.draw.line(self.screen, (255,240,60), (cx+7, cy), (cx+17, cy), 3)
            pygame.draw.line(self.screen, (255,240,60), (cx+13, cy), (cx+13, cy+5), 2)

    def draw_minimap(self):
        w, h = COLS*MAP_TILE, ROWS*MAP_TILE
        origin = (WIDTH-w-8, 8)
        pygame.draw.rect(self.screen, (0,0,0), (origin[0]-2, origin[1]-2, w+4, h+4))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell == WALL: col = (60,50,70)
                elif cell == CHEST: col = (200,160,30)
                elif cell == KEY: col = (255,240,60)
                elif cell in TRAPS: col = (220,90,40)
                else: col = (200,190,170)
                pygame.draw.rect(self.screen, col, (origin[0]+c*MAP_TILE, origin[1]+r*MAP_TILE, MAP_TILE, MAP_TILE))
        if self.guard:
            gx = origin[0] + self.guard.rect.centerx*MAP_TILE//TILE
            gy = origin[1] + self.guard.rect.centery*MAP_TILE//TILE
            pygame.draw.circle(self.screen, (200,40,40), (gx, gy), 3)
        px = origin[0] + self.player.rect.centerx*MAP_TILE//TILE
        py = origin[1] + self.player.rect.centery*MAP_TILE//TILE
        pygame.draw.circle(self.screen, (60,120,220), (px, py), 3)
        pygame.draw.circle(self.screen, (255,255,255), (px, py), 3, 1)

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
