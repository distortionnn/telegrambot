import aiosqlite
import sqlite3
import time
import subprocess
from outline_vpn.outline_vpn import OutlineVPN




CONFIG={}
DBCONNECT="data.sqlite"

class User:
    def __init__(self):
        self.id = None
        self.tgid = None
        self.subscription = None
        self.trial_subscription = True
        self.registered = False
        self.username = None
        self.fullname = None

    @classmethod
    async def GetInfo(cls, tgid):
        self = User()
        self.tgid = tgid
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM userss where tgid=?",(tgid,))
        log = await c.fetchone()
        await c.close()
        await db.close()
        if not log is None:
            self.id = log["id"]
            self.subscription = log["subscription"]
            self.trial_subscription = log["banned"]
            self.registered = True
            self.username = log["username"]
            self.fullname = log["fullname"]
        else:
            self.registered = False

        return self


    async def PaymentInfo(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM payments where tgid=?", (self.tgid,))
        log = await c.fetchone()
        await c.close()
        await db.close()
        return log

    async def CancelPayment(self):
        db = await aiosqlite.connect(DBCONNECT)
        await db.execute(f"DELETE FROM payments where tgid=?",
                         (self.tgid,))
        await db.commit()

    async def NewPay(self,bill_id,summ,time_to_add,mesid):
        pay_info = await self.PaymentInfo()
        #print(pay_info)
        if pay_info is None:
            db = await aiosqlite.connect(DBCONNECT)
            await db.execute(f"INSERT INTO payments (tgid,bill_id,amount,time_to_add,mesid) values (?,?,?,?,?)",
                             (self.tgid, str(bill_id),summ,int(time_to_add),str(mesid)))
            await db.commit()
            db.close()



    async def GetAllPaymentsInWork(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM payments")
        log = await c.fetchall()
        await c.close()
        await db.close()
        return log

    async def Adduser(self,username,full_name):
        if self.registered == False:
            db = await aiosqlite.connect(DBCONNECT)
            await db.execute(f"INSERT INTO userss (tgid,subscription,username,fullname) values (?,?,?,?)", (self.tgid,str(int(time.time())+int(CONFIG['trial_period'])),str(username),str(full_name)))
            await db.commit()
            await db.close()
            self.registered = True


    async def GetAllUsers(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM userss")
        log = await c.fetchall()
        await c.close()
        await db.close()
        return log

    async def GetAllUsersWithSub(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM userss where subscription > ?",(str(int(time.time())),))
        log = await c.fetchall()
        await c.close()
        await db.close()
        return log




    async def CheckNewNickname(self,message):
        try:
            username = "@" + str(message.from_user.username)
        except:
            username = str(message.from_user.id)

        if message.from_user.full_name!=self.fullname or username!=self.username:
            db = await aiosqlite.connect(DBCONNECT)
            db.row_factory = sqlite3.Row
            await db.execute(f"Update userss set username = ?, fullname = ? where id = ?", (username,message.from_user.full_name,self.id))
            await db.commit()
            db.close()

    async def CheckClient(self, url, cersha):
        try:
            client = OutlineVPN(api_url=url, cert_sha256=cersha)
            status = client.get_metrics_status()
            return True
        except:
            return False

    async def Showkeys(self,url,cersha):
        try:
            client = OutlineVPN(api_url=url,cert_sha256=cersha)
            keys = ''
            for key in client.get_keys():
                keys += f"{key.access_url}\n"
            return keys
        except:
            return "Error conected"


    async def GetServers(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM servers")
        log = await c.fetchall()
        await c.close()
        await db.close()
        result = {}

        for i in range(len(log)):
            client = OutlineVPN(api_url=log[i][4], cert_sha256=log[i][5])
            try:
                keys = client.get_keys()
            except:
                keys = "Ошибка подключения"
            if len(keys) >= CONFIG['max_people_server']:
                db = await aiosqlite.connect(DBCONNECT)
                db.row_factory = sqlite3.Row
                await db.execute(f"Update servers set space = ? where url = ?", (False, log[i][4]))
                await db.commit()
                await db.close()
            else:
                db = await aiosqlite.connect(DBCONNECT)
                db.row_factory = sqlite3.Row
                await db.execute(f"Update servers set space = ? where url = ?", (True, log[i][4]))
                await db.commit()
                await db.close()

            if type(keys) == type([]):
                space = f"{len(keys)} из {CONFIG['max_people_server']}"
            else:
                space = keys
            result[i] = {}
            result[i]["s"] = log[i]
            result[i]["space"] = space


        return result

    async def countSpace(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM servers")
        log = await c.fetchall()
        await c.close()
        await db.close()
        sum = 0
        allServerCount = 0
        for i in range(len(log)):
            client = OutlineVPN(api_url=log[i][4], cert_sha256=log[i][5])
            try:
                keys = client.get_keys()
            except:
                keys = "Ошибка подключения"

            if type(keys) == type([]):
                sum += len(keys)
            allServerCount += 1*CONFIG['max_people_server']
        result = [allServerCount,sum]
        return result

    async def AddServer(self,name,ip,password,url,cersha):
            try:
                db = await aiosqlite.connect(DBCONNECT)
                await db.execute(f"INSERT INTO servers (name,ip,password,url,certsha,space) values (?,?,?,?,?,?)", (
                str(name), str(ip), str(password), str(url), str(cersha),True))
                await db.commit()
                await db.close()
                return True
            except:
                return False

    async def DeleteServer(self,ip):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM servers WHERE ip=?", (ip,))
        servers = await c.fetchall()
        c = await db.execute(f"SELECT * FROM userss WHERE server=?", (servers[0][4],))
        log = await c.fetchall()
        for users in log:
            await db.execute(f"Update userss set server = ? where tgid = ?", (None,users[1]))
            await db.commit()
        await db.execute(f"DELETE FROM static_profiles where url=?", (servers[0][4],))
        await db.commit()
        await db.execute(f"DELETE FROM servers where ip=?",(ip,))
        await db.commit()
        await c.close()
        await db.close()
        return True

    async def freeServer(self,max_people_server):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM servers WHERE space = true;")
        log = await c.fetchall()
        await c.close()
        await db.close()
        finalServer = {}
        try:
            for server in log:
                client = OutlineVPN(api_url=server[4], cert_sha256=server[5])
                if len(client.get_keys()) < int(max_people_server):
                    finalServer = {"url":server[4],"cert_sha256":server[5]}
                    break
            return finalServer
        except:
            return {}




    async def AddConfigServer(self,id,freeServer,max_people_server):
        client = OutlineVPN(api_url=freeServer['url'], cert_sha256=freeServer['cert_sha256'])
        try:
            new_key = client.create_key(key_name=str(id))
        except:
            return "Error conect"
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        await db.execute(f"Update userss set server = ? where tgid = ?", (freeServer['url'], id))
        await db.commit()
        try:
            if len(client.get_keys()) >= int(max_people_server):
                await db.execute(f"Update servers set space = ? where url = ?",(False, freeServer['url']))
                await db.commit()

            await db.close()
            return new_key.access_url
        except:
            await db.close()
            return "Error conect"

    async def AdminAddConfigServer(self,url,sha256,keyname):
        try:
            client = OutlineVPN(api_url=url, cert_sha256=sha256)
            new_key = client.create_key(key_name=keyname)
            db = await aiosqlite.connect(DBCONNECT)
            db.row_factory = sqlite3.Row
            if len(client.get_keys()) >= CONFIG['max_people_server']:
                await db.execute(f"Update servers set space = ? where url = ?",(False, freeServer['url']))
                await db.commit()

            await db.close()
            return new_key.access_url
        except:
            return ""

    async def CheckUserServer(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM userss where tgid = ?", (self.tgid,))
        log = await c.fetchall()
        await c.close()
        await db.close()
        server = log[0][7]
        if(server != None):
            return True
        else:
            return False

    async def GetUserServer(self):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM userss where tgid = ?", (self.tgid,))
        url = await c.fetchall()
        url = url[0][7]
        c = await db.execute(f"SELECT * FROM servers where url = ?", (url,))
        cert_sha256 = await c.fetchall()
        cert_sha256 = cert_sha256[0][5]
        await c.close()
        await db.close()
        config = ''
        client = OutlineVPN(api_url=url, cert_sha256=cert_sha256)
        try:
            for key in client.get_keys():
                if key.name == str(self.tgid):
                    config = key.access_url
            return config
        except:
            return ""

    async def GetAdminServer(self,url,namekey):
        db = await aiosqlite.connect(DBCONNECT)
        db.row_factory = sqlite3.Row
        c = await db.execute(f"SELECT * FROM servers where url = ?", (url,))
        cert_sha256 = await c.fetchall()
        if len(cert_sha256) == 0:
            return "Ошибка вы неправельно добавили этот прифиль"
        cert_sha256 = cert_sha256[0][5]
        await c.close()
        await db.close()
        config = ''
        client = OutlineVPN(api_url=url, cert_sha256=cert_sha256)
        try:
            for key in client.get_keys():
                if key.name == str(namekey):
                    config = key.access_url
            return config
        except:
            return ""
