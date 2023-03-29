import utime
from math import fabs
from machine import I2C,Pin
i2c=I2C(1,sda=Pin(0),scl=Pin(1),freq=400000)

def gesinit():
    i2c.write(57,b'\x81\xfc')  #ADC积分时间寄存器
    # print(i2c.readfrom_mem(57,0x81,1))
    i2c.write(57,b'\x8f\x01')   # 接近脉冲计数寄存器
    # print(i2c.readfrom_mem(57,0x8f,1))

    i2c.write(57,b'\x80\x00')   #将启用寄存器bit[0]   先手动关闭电源
    # print(i2c.readfrom_mem(57,0x80,1))
    utime.sleep_ms(30)

    i2c.write(57,b'\x80\x01')   #sleep30ms 手动打开电源
    # print(i2c.readfrom_mem(57,0x80,1))
    utime.sleep_ms(30)

    i2c.write(57,b'\xa2\x40')   #手势配置一寄存器 在FIFO读4个数据集后中断
    # print(i2c.readfrom_mem(57,0xa2,1))
    i2c.write(57,b'\xA3\x40')   #手势配置二寄存器 手势增益设置为4x,LED电流驱动为100mA
    # print(i2c.readfrom_mem(57,0xA3,1))
    i2c.write(57,b'\xA0\x32')   #手势接近输入阈值寄存器 设置为0x32
    # print(i2c.readfrom_mem(57,0xA0,1))
    i2c.write(57,b'\xA6\xc9')   #手势脉冲计数和长度寄存器  32微秒 脉冲数为10
    # print(i2c.readfrom_mem(57,0xA6,1))
    i2c.write(57,b'\x80\x05')
    # print(i2c.readfrom_mem(57,0x80,1))
    i2c.write(57,b'\x80\x45')   #一步步将0X80寄存器的bit[0],bit[2],[6]打开
    # print(i2c.readfrom_mem(57,0x80,1))
    i2c.write(57,b'\xab\x01')   #手势配置四寄存器 手动打开GMODE
    # print(i2c.readfrom_mem(57,0xab,1))

def getges():      #获取手势
    gesinit()      #初始化寄存器
    dcount=ucount=lcount=rcount=0
    while 1:
        ges=''
        up_down_diff=left_right_diff=0
        while 1:

            if (i2c.readfrom_mem(57,0xaf,1)[0]==0):
                # print("useless")        0xaf表示手势寄存器FIFO状态 不能为0
                continue
            else:
                ae=i2c.readfrom_mem(57,0xae,1)    #0xae寄存器表示可用于读取的数据集的数量
                if (ae==0):
                    continue
                # else :
                #     print(ae)   用于检验能读几个数据集
                gesture_num=i2c.readfrom_mem(57,0xfc,ae[0])            #读取总共的数据集
                container=i2c.readfrom_mem(57,0xfc,4)         #从手势数据寄存器当中读取手势数据 0xfc-0xff 32*4字节的FIFO
                break

        if fabs(container[0]-container[1])>50:           #数值方向判断阈值
            up_down_diff+=container[0]-container[1]
        if fabs(container[2]-container[3])>50:           #水平方向判断阈值
            left_right_diff+=container[2]-container[3]
        #判断具体是哪个方向的手势
        if up_down_diff!=0:
            if up_down_diff<0:
                if dcount>0:
                    ges='down'
                else:
                    ucount+=1
            elif up_down_diff>0:
                if ucount>0:
                    ges='up'
                else:
                    dcount+=1
        if left_right_diff!=0:
            if left_right_diff<0:
                if rcount>0:
                    ges='right'
                else:
                    lcount+=1
            if left_right_diff>0:
                if lcount>0:
                    ges='left'
                else:
                    rcount+=1
        if ges!='':
            dcount=ucount=lcount=rcount=0
            # print(ges)
            return ges


def toget():   #获取手势函数
    while True:
        ges=getges()
        if ges:
            break
        utime.sleep_ms(500)
    # print(ges)
    return ges    #返回手势

# while 1:
#     toget()
#     utime.sleep_ms(1000)




