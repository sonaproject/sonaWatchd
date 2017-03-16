class CMD_PROC():
    @staticmethod
    def proc_dis_resource(system, param):
        return "return proc_dis_resource [sys = " + system + " param = " + param + "]"

    @staticmethod
    def proc_dis_onos(system, param):
        return "return proc_dis_onos [sys = " + system + " param = " + param + "]"

    @staticmethod
    def proc_dis_log(system, param):
        return "return proc_dis_log [sys = " + system + " param = " + param + "]"