from machine import ADC, SPI, Pin
import st7789
import utime
import math
import APDS9960
import urandom
import network
import ujson
import gc
from simple import MQTTClient   #MQTT协议
import utime

spi = SPI(0, baudrate=40000000, polarity=1, phase=0, bits=8, endia=0, sck=Pin(6), mosi=Pin(8))
screen = st7789.ST7789(spi, 240, 240, reset=Pin(11, func=Pin.GPIO, dir=Pin.OUT), dc=Pin(7, func=Pin.GPIO, dir=Pin.OUT))
screen.init()

utime.sleep_ms(1000)

screen.draw_string(40, 220, "Edited by Jsaon", size=2)  # 游戏未开始 初始加载界面
utime.sleep_ms(3000)

_map_data = [       #用于存放方块的列表
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0]
]


def reset():
    # '''重新设置游戏数据,将地图恢复为初始状态，数字0表示格子为空，没有数字。并且加入两个数据 2 作用初始状态'''
    _map_data[:] = []  # _map_data.clear()
    _map_data.append([0, 0, 0, 0])
    _map_data.append([0, 0, 0, 0])
    _map_data.append([0, 0, 0, 0])
    _map_data.append([0, 0, 0, 0])
    fill2()# 在空白地图上填充两个2
    fill2()


def get_space_count():
    """获取没有数字的方格的数量,如果数量为0则说有无法填充新数据，游戏即将结束
    """
    count = 0
    for r in _map_data:
        count += r.count(0)
    return count


def get_score():
    '''获取游戏的分数,得分规则是每次有两个数加在一起则生成相应的分数。
    如 2 和 2 合并后得4分, 8 和 8 分并后得 16分.
    根据一个大于2的数字就可以知道他共合并了多少次，可以直接算出分数:
    如:
       4 一定由两个2合并，得4分
       8 一定由两个4合并,则计:8 + 4 + 4 得16分
       ... 以此类推
    '''
    score = 0
    for r in _map_data:
        for c in r:
            score += 0 if c < 4 else c * int((math.log(c, 2) - 1.0))
    return score  # 导入数学模块


def fill2():
    # 默认只产生一个2
    '''填充2到空位置，如果填度成功返回True,如果已满，则返回False'''
    blank_count = get_space_count()  # 得到地图上空白位置的个数
    if 0 == blank_count:
        return False
    # 生成随机位置, 如，当只有四个空时，则生成0~3的数，代表自左至右，自上而下的空位置
    pos = urandom.randint(0, blank_count - 1)
    offset = 0
    for row in _map_data:  # row为行row
        for col in range(4):  # col 为列，column
            if 0 == row[col]:
                if offset == pos:
                    # 把2填充到第row行，第col列的位置，返回True
                    row[col] = 2
                    return True
                offset += 1


def is_gameover():
    """判断游戏是否结束,如果结束返回True,否是返回False
    """
    for r in _map_data:
        # 如果水平方向还有0,则游戏没有结束
        if r.count(0):
            return False
        # 水平方向如果有两个相邻的元素相同，应当是可以合并的，则游戏没有结束
        for i in range(3):
            if r[i] == r[i + 1]:
                return False
    for c in range(4):
        # 竖直方向如果有两个相邻的元素相同，应当可以合并的，则游戏没有结束
        for r in range(3):
            if _map_data[r][c] == _map_data[r + 1][c]:
                return False
    # 以上都没有，则游戏结束
    return True


def _left_move_number(line):
        #方块移动函数
    '''左移一行数字,如果有数据移动则返回True，否则返回False:
        如: line = [0, 2, 0, 8] 即表达如下一行:
            +---+---+---+---+
            | 0 | 2 | 0 | 8 |      <----向左移动
            +---+---+---+---+
        此行数据需要左移三次:
          第一次左移结果:
            +---+---+---+---+
            | 2 | 0 | 8 | 0 |
            +---+---+---+---+
          第二次左移结果:
            +---+---+---+---+
            | 2 | 8 | 0 | 0 |
            +---+---+---+---+
          第三次左移结果:
            +---+---+---+---+
            | 2 | 8 | 0 | 0 |  # 因为最左则为2,所以8不动
            +---+---+---+---+
         最终结果: line = [4, 8, 0, 0]
        '''
    moveflag = False  # 是否移动的标识,先假设没有移动
    for _ in range(3):  # 重复执行下面算法三次
        for i in range(3):  # i为索引
            if 0 == line[i]:  # 此处有空位，右侧相邻数字向左侧移动，右侧填空白
                moveflag = True
                line[i] = line[i + 1]
                line[i + 1] = 0
    return moveflag


def _left_marge_number(line):
    #方块合并函数
    '''向左侧进行相同单元格合并,合并结果放在左侧,右侧补零
    如: line = [2, 2, 4, 4] 即表达如下一行:
        +---+---+---+---+
        | 2 | 2 | 4 | 4 |
        +---+---+---+---+
    全并后的结果为:
        +---+---+---+---+
        | 4 | 0 | 8 | 0 |
        +---+---+---+---+
    最终结果: line = [4, 8, 0, 0]
    '''
    for i in range(3):
        if line[i] == line[i + 1]:
            moveflag = True
            line[i] *= 2  # 左侧翻倍
            line[i + 1] = 0  # 右侧归零


def _left_move_aline(line):
    #左移方块 移动 合并 移动
    '''左移一行数据,如果有数据移动则返回True，否则返回False:
    如: line = [2, 0, 2, 8] 即表达如下一行:
        +---+---+---+---+
        | 2 | 0 | 2 | 8 |      <----向左移动
        +---+---+---+---+
    左移算法分为三步:
        1. 将所有数字向左移动来填补左侧空格,即:
            +---+---+---+---+
            | 2 | 2 | 8 |   |
            +---+---+---+---+
        2. 判断是否发生碰幢，如果两个相临且相等的数值则说明有碰撞需要合并,
           合并结果靠左，右则填充空格
            +---+---+---+---+
            | 4 |   | 8 |   |
            +---+---+---+---+
        3. 再重复第一步，将所有数字向左移动来填补左侧空格,即:
            +---+---+---+---+
            | 4 | 8 |   |   |
            +---+---+---+---+
        最终结果: line = [4, 8, 0, 0]
    '''
    moveflag = False
    if _left_move_number(line):
        moveflag = True
    if _left_marge_number(line):
        moveflag = True
    if _left_move_number(line):
        moveflag = True
    return moveflag


def left():
    #向左挥动手势的算法
    moveflag = False  # moveflag 是否成功移动数字标志位,如果有移动则为真值,原地图不变则为假值

    # 将第一行都向左移动.如果有移动就返回True
    for line in _map_data:
        if _left_move_aline(line):
            moveflag = True
    return moveflag


def right():
    """向右挥动手势的算法
    选将屏幕进行左右对调，对调后，原来的向右滑动即为现在的向左滑动
    滑动完毕后，再次左右对调回来
    """
    # 左右对调
    for r in _map_data:
        r.reverse()
    moveflag = left()  # 向左滑动
    # 再次左右对调
    for r in _map_data:
        r.reverse()
    return moveflag


def up():
    """向上挥动手势的算法
    先把每一列都自上而下放入一个列表中line中，然后执行向左滑动，
    滑动完成后再将新位置摆回到原来的一列中
    """
    moveflag = False
    line = [0, 0, 0, 0]  # 先初始化一行，准备放入数据
    for col in range(4):  # 先取出每一列
        # 把一列中的每一行数入放入到line中
        for row in range(4):
            line[row] = _map_data[row][col]
        # 将当前列进行上移，即line 左移
        if (_left_move_aline(line)):
            moveflag = True
        # 把左移后的 line中的数据填充回原来的一列
        for row in range(4):
            _map_data[row][col] = line[row]
    return moveflag


def down():
    """向下挥动手势的算法
    选将屏幕进行上下对调，对调后，原来的向下滑动即为现在的向上滑动
    滑动完毕后，再次上下对调回来
    """
    _map_data.reverse()
    moveflag = up()  # 上滑
    _map_data.reverse()
    return moveflag


def print_info():    #打印当前游戏状态
    screen.fill(st7789.color565(245, 222, 179))                         #背景
    screen.fill_rect(24, 24, 192, 148, st7789.color565(189, 252, 201))  # 实心矩形
    screen.rect(24, 24, 192, 148, st7789.color565(61, 145, 64))  # 矩形边
    screen.vline(72, 24, 148, st7789.color565(0, 0, 0))  # 竖线
    screen.vline(120, 24, 148, st7789.color565(0, 0, 0))
    screen.vline(168, 24, 148, st7789.color565(0, 0, 0))
    screen.hline(24, 61, 192, st7789.color565(0, 0, 0))  # 横线
    screen.hline(24, 98, 192, st7789.color565(0, 0, 0))
    screen.hline(24, 135, 192, st7789.color565(0, 0, 0))
    for i in range(4):
        for j in range(4):
            if _map_data[i][j] != 0:
                screen.draw_string(j * 48 + 30, i * 37 + 30, str(_map_data[i][j]), color=st7789.RED,    #数字显示
                                   bg=st7789.color565(189, 252, 201), size=2)


def connectWIFI():                          #链接WiFi 为发送信息到MQTT协议做准备
    print('Connecting wifi...')
    sta_wlan = network.WLAN(network.STA_IF)
    sta_wlan.active(True)
    # sta_wlan.connect('WiFiName', 'WiFikey', security=network.AUTH_PSK)
    sta_wlan.connect('fhe142', '18042475359', security=network.AUTH_PSK)
    while (sta_wlan.config() == '0.0.0.0'):
        utime.sleep(1)
    print('Connected...')

connectWIFI()              #连接WiFi

screen.fill(st7789.color565(245, 222, 179))  # 背景颜色
utime.sleep_ms(500)

#游戏开始界面  向右挥动手势以开始
screen.draw_string(20, 24, "Wave", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)
utime.sleep_ms(500)
screen.draw_string(20, 80, "To The Right ", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=3)
utime.sleep_ms(500)
screen.draw_string(20, 130, "To Start", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)
utime.sleep_ms(500)
screen.draw_string(24, 185, "Game!", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=5)

score = 0
gameover = False  # 初始化游戏分数和GAMEOVER判定

while 1:  # 游戏正式开始，向右挥动手势开始游戏，初始加载两个2
    gesture = APDS9960.toget()  # 获取手势信息
    if (gesture == 'right'):      #检测到向右挥手 重置列表开始游戏 打印初始情况
        reset()
        print_info()
        screen.draw_string(24, 200, "Score:", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=3)
        screen.draw_string(135, 195, str(score), color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)
        break

utime.sleep_ms(500)
# count = 0
while 1:
    gameover = is_gameover()  # 判断游戏是否结束，若结束提示结束并且打印成绩，跳出循环
    if (gameover == True):
        score = get_score()
        screen.fill(st7789.color565(245, 222, 179))
        screen.draw_string(25, 90, "GAME OVER!", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)
        screen.draw_string(24, 200, "Score:", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=3)
        screen.draw_string(135, 195, str(score), color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)
        break

    gesture = APDS9960.toget()    #获取手势信息
    if gesture != '':
        # count += 1                 #展示使用count
        # print(count)
        if gesture == 'right':      #检测到向右挥手 右移 随机生成2
            right()
            fill2()
            print_info()
            print("right")
            score = get_score()    #获取分数并打印
            screen.draw_string(24, 200, "Score:", color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=3)
            screen.draw_string(135, 195, str(score), color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=4)
            utime.sleep_ms(500)
        elif gesture == 'left':
            left()
            fill2()
            print_info()
            print("left")
            score = get_score()
            screen.draw_string(24, 200, "Score:", color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=3)
            screen.draw_string(135, 195, str(score), color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=4)
            utime.sleep_ms(500)
        elif gesture == 'up':
            up()
            fill2()
            print_info()
            print("up")
            score = get_score()
            screen.draw_string(24, 200, "Score:", color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=3)
            screen.draw_string(135, 195, str(score), color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=4)
            utime.sleep_ms(500)
        elif gesture == 'down':
            down()
            fill2()
            print_info()
            print("down")
            score = get_score()
            screen.draw_string(24, 200, "Score:", color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=3)
            screen.draw_string(135, 195, str(score), color=st7789.BLUE, bg=st7789.color565(245, 222, 179), size=4)
            utime.sleep_ms(500)
    # if count == 10:     #测试及展示用！
    #     break
    # utime.sleep_ms(300)

score = get_score()     获取最终分数
SERVER = '118.31.53.253'  # 输入mqtt服务器的地址
CLIENT_ID = '2048game'  # 连入mqtt的设备名称
TOPIC = b'gamescore'  # waffle订阅的mqtt主题

client = MQTTClient(CLIENT_ID, SERVER)
client.connect()     #连接MQTT服务器

info = {                    #玩家name&value
    "name": "player1",
    "value": score
}

info = ujson.dumps(info)               #将信息转化为json格式
client.publish(TOPIC, info)                #向MQTT服务器发送json格式的信息

#测试&展示用
# print("1")
# screen.fill(st7789.color565(245, 222, 179))
# screen.draw_string(28, 90, "GAME OVER!", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)
# screen.draw_string(24, 200, "Score:", color=st7789.RED, bg=st7789.color565(245, 222, 179), size=3)
# screen.draw_string(135, 195, str(score), color=st7789.RED, bg=st7789.color565(245, 222, 179), size=4)