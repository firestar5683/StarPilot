#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_581108018479819489) {
   out_581108018479819489[0] = delta_x[0] + nom_x[0];
   out_581108018479819489[1] = delta_x[1] + nom_x[1];
   out_581108018479819489[2] = delta_x[2] + nom_x[2];
   out_581108018479819489[3] = delta_x[3] + nom_x[3];
   out_581108018479819489[4] = delta_x[4] + nom_x[4];
   out_581108018479819489[5] = delta_x[5] + nom_x[5];
   out_581108018479819489[6] = delta_x[6] + nom_x[6];
   out_581108018479819489[7] = delta_x[7] + nom_x[7];
   out_581108018479819489[8] = delta_x[8] + nom_x[8];
   out_581108018479819489[9] = delta_x[9] + nom_x[9];
   out_581108018479819489[10] = delta_x[10] + nom_x[10];
   out_581108018479819489[11] = delta_x[11] + nom_x[11];
   out_581108018479819489[12] = delta_x[12] + nom_x[12];
   out_581108018479819489[13] = delta_x[13] + nom_x[13];
   out_581108018479819489[14] = delta_x[14] + nom_x[14];
   out_581108018479819489[15] = delta_x[15] + nom_x[15];
   out_581108018479819489[16] = delta_x[16] + nom_x[16];
   out_581108018479819489[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7407620403679899755) {
   out_7407620403679899755[0] = -nom_x[0] + true_x[0];
   out_7407620403679899755[1] = -nom_x[1] + true_x[1];
   out_7407620403679899755[2] = -nom_x[2] + true_x[2];
   out_7407620403679899755[3] = -nom_x[3] + true_x[3];
   out_7407620403679899755[4] = -nom_x[4] + true_x[4];
   out_7407620403679899755[5] = -nom_x[5] + true_x[5];
   out_7407620403679899755[6] = -nom_x[6] + true_x[6];
   out_7407620403679899755[7] = -nom_x[7] + true_x[7];
   out_7407620403679899755[8] = -nom_x[8] + true_x[8];
   out_7407620403679899755[9] = -nom_x[9] + true_x[9];
   out_7407620403679899755[10] = -nom_x[10] + true_x[10];
   out_7407620403679899755[11] = -nom_x[11] + true_x[11];
   out_7407620403679899755[12] = -nom_x[12] + true_x[12];
   out_7407620403679899755[13] = -nom_x[13] + true_x[13];
   out_7407620403679899755[14] = -nom_x[14] + true_x[14];
   out_7407620403679899755[15] = -nom_x[15] + true_x[15];
   out_7407620403679899755[16] = -nom_x[16] + true_x[16];
   out_7407620403679899755[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_6259423772009568262) {
   out_6259423772009568262[0] = 1.0;
   out_6259423772009568262[1] = 0.0;
   out_6259423772009568262[2] = 0.0;
   out_6259423772009568262[3] = 0.0;
   out_6259423772009568262[4] = 0.0;
   out_6259423772009568262[5] = 0.0;
   out_6259423772009568262[6] = 0.0;
   out_6259423772009568262[7] = 0.0;
   out_6259423772009568262[8] = 0.0;
   out_6259423772009568262[9] = 0.0;
   out_6259423772009568262[10] = 0.0;
   out_6259423772009568262[11] = 0.0;
   out_6259423772009568262[12] = 0.0;
   out_6259423772009568262[13] = 0.0;
   out_6259423772009568262[14] = 0.0;
   out_6259423772009568262[15] = 0.0;
   out_6259423772009568262[16] = 0.0;
   out_6259423772009568262[17] = 0.0;
   out_6259423772009568262[18] = 0.0;
   out_6259423772009568262[19] = 1.0;
   out_6259423772009568262[20] = 0.0;
   out_6259423772009568262[21] = 0.0;
   out_6259423772009568262[22] = 0.0;
   out_6259423772009568262[23] = 0.0;
   out_6259423772009568262[24] = 0.0;
   out_6259423772009568262[25] = 0.0;
   out_6259423772009568262[26] = 0.0;
   out_6259423772009568262[27] = 0.0;
   out_6259423772009568262[28] = 0.0;
   out_6259423772009568262[29] = 0.0;
   out_6259423772009568262[30] = 0.0;
   out_6259423772009568262[31] = 0.0;
   out_6259423772009568262[32] = 0.0;
   out_6259423772009568262[33] = 0.0;
   out_6259423772009568262[34] = 0.0;
   out_6259423772009568262[35] = 0.0;
   out_6259423772009568262[36] = 0.0;
   out_6259423772009568262[37] = 0.0;
   out_6259423772009568262[38] = 1.0;
   out_6259423772009568262[39] = 0.0;
   out_6259423772009568262[40] = 0.0;
   out_6259423772009568262[41] = 0.0;
   out_6259423772009568262[42] = 0.0;
   out_6259423772009568262[43] = 0.0;
   out_6259423772009568262[44] = 0.0;
   out_6259423772009568262[45] = 0.0;
   out_6259423772009568262[46] = 0.0;
   out_6259423772009568262[47] = 0.0;
   out_6259423772009568262[48] = 0.0;
   out_6259423772009568262[49] = 0.0;
   out_6259423772009568262[50] = 0.0;
   out_6259423772009568262[51] = 0.0;
   out_6259423772009568262[52] = 0.0;
   out_6259423772009568262[53] = 0.0;
   out_6259423772009568262[54] = 0.0;
   out_6259423772009568262[55] = 0.0;
   out_6259423772009568262[56] = 0.0;
   out_6259423772009568262[57] = 1.0;
   out_6259423772009568262[58] = 0.0;
   out_6259423772009568262[59] = 0.0;
   out_6259423772009568262[60] = 0.0;
   out_6259423772009568262[61] = 0.0;
   out_6259423772009568262[62] = 0.0;
   out_6259423772009568262[63] = 0.0;
   out_6259423772009568262[64] = 0.0;
   out_6259423772009568262[65] = 0.0;
   out_6259423772009568262[66] = 0.0;
   out_6259423772009568262[67] = 0.0;
   out_6259423772009568262[68] = 0.0;
   out_6259423772009568262[69] = 0.0;
   out_6259423772009568262[70] = 0.0;
   out_6259423772009568262[71] = 0.0;
   out_6259423772009568262[72] = 0.0;
   out_6259423772009568262[73] = 0.0;
   out_6259423772009568262[74] = 0.0;
   out_6259423772009568262[75] = 0.0;
   out_6259423772009568262[76] = 1.0;
   out_6259423772009568262[77] = 0.0;
   out_6259423772009568262[78] = 0.0;
   out_6259423772009568262[79] = 0.0;
   out_6259423772009568262[80] = 0.0;
   out_6259423772009568262[81] = 0.0;
   out_6259423772009568262[82] = 0.0;
   out_6259423772009568262[83] = 0.0;
   out_6259423772009568262[84] = 0.0;
   out_6259423772009568262[85] = 0.0;
   out_6259423772009568262[86] = 0.0;
   out_6259423772009568262[87] = 0.0;
   out_6259423772009568262[88] = 0.0;
   out_6259423772009568262[89] = 0.0;
   out_6259423772009568262[90] = 0.0;
   out_6259423772009568262[91] = 0.0;
   out_6259423772009568262[92] = 0.0;
   out_6259423772009568262[93] = 0.0;
   out_6259423772009568262[94] = 0.0;
   out_6259423772009568262[95] = 1.0;
   out_6259423772009568262[96] = 0.0;
   out_6259423772009568262[97] = 0.0;
   out_6259423772009568262[98] = 0.0;
   out_6259423772009568262[99] = 0.0;
   out_6259423772009568262[100] = 0.0;
   out_6259423772009568262[101] = 0.0;
   out_6259423772009568262[102] = 0.0;
   out_6259423772009568262[103] = 0.0;
   out_6259423772009568262[104] = 0.0;
   out_6259423772009568262[105] = 0.0;
   out_6259423772009568262[106] = 0.0;
   out_6259423772009568262[107] = 0.0;
   out_6259423772009568262[108] = 0.0;
   out_6259423772009568262[109] = 0.0;
   out_6259423772009568262[110] = 0.0;
   out_6259423772009568262[111] = 0.0;
   out_6259423772009568262[112] = 0.0;
   out_6259423772009568262[113] = 0.0;
   out_6259423772009568262[114] = 1.0;
   out_6259423772009568262[115] = 0.0;
   out_6259423772009568262[116] = 0.0;
   out_6259423772009568262[117] = 0.0;
   out_6259423772009568262[118] = 0.0;
   out_6259423772009568262[119] = 0.0;
   out_6259423772009568262[120] = 0.0;
   out_6259423772009568262[121] = 0.0;
   out_6259423772009568262[122] = 0.0;
   out_6259423772009568262[123] = 0.0;
   out_6259423772009568262[124] = 0.0;
   out_6259423772009568262[125] = 0.0;
   out_6259423772009568262[126] = 0.0;
   out_6259423772009568262[127] = 0.0;
   out_6259423772009568262[128] = 0.0;
   out_6259423772009568262[129] = 0.0;
   out_6259423772009568262[130] = 0.0;
   out_6259423772009568262[131] = 0.0;
   out_6259423772009568262[132] = 0.0;
   out_6259423772009568262[133] = 1.0;
   out_6259423772009568262[134] = 0.0;
   out_6259423772009568262[135] = 0.0;
   out_6259423772009568262[136] = 0.0;
   out_6259423772009568262[137] = 0.0;
   out_6259423772009568262[138] = 0.0;
   out_6259423772009568262[139] = 0.0;
   out_6259423772009568262[140] = 0.0;
   out_6259423772009568262[141] = 0.0;
   out_6259423772009568262[142] = 0.0;
   out_6259423772009568262[143] = 0.0;
   out_6259423772009568262[144] = 0.0;
   out_6259423772009568262[145] = 0.0;
   out_6259423772009568262[146] = 0.0;
   out_6259423772009568262[147] = 0.0;
   out_6259423772009568262[148] = 0.0;
   out_6259423772009568262[149] = 0.0;
   out_6259423772009568262[150] = 0.0;
   out_6259423772009568262[151] = 0.0;
   out_6259423772009568262[152] = 1.0;
   out_6259423772009568262[153] = 0.0;
   out_6259423772009568262[154] = 0.0;
   out_6259423772009568262[155] = 0.0;
   out_6259423772009568262[156] = 0.0;
   out_6259423772009568262[157] = 0.0;
   out_6259423772009568262[158] = 0.0;
   out_6259423772009568262[159] = 0.0;
   out_6259423772009568262[160] = 0.0;
   out_6259423772009568262[161] = 0.0;
   out_6259423772009568262[162] = 0.0;
   out_6259423772009568262[163] = 0.0;
   out_6259423772009568262[164] = 0.0;
   out_6259423772009568262[165] = 0.0;
   out_6259423772009568262[166] = 0.0;
   out_6259423772009568262[167] = 0.0;
   out_6259423772009568262[168] = 0.0;
   out_6259423772009568262[169] = 0.0;
   out_6259423772009568262[170] = 0.0;
   out_6259423772009568262[171] = 1.0;
   out_6259423772009568262[172] = 0.0;
   out_6259423772009568262[173] = 0.0;
   out_6259423772009568262[174] = 0.0;
   out_6259423772009568262[175] = 0.0;
   out_6259423772009568262[176] = 0.0;
   out_6259423772009568262[177] = 0.0;
   out_6259423772009568262[178] = 0.0;
   out_6259423772009568262[179] = 0.0;
   out_6259423772009568262[180] = 0.0;
   out_6259423772009568262[181] = 0.0;
   out_6259423772009568262[182] = 0.0;
   out_6259423772009568262[183] = 0.0;
   out_6259423772009568262[184] = 0.0;
   out_6259423772009568262[185] = 0.0;
   out_6259423772009568262[186] = 0.0;
   out_6259423772009568262[187] = 0.0;
   out_6259423772009568262[188] = 0.0;
   out_6259423772009568262[189] = 0.0;
   out_6259423772009568262[190] = 1.0;
   out_6259423772009568262[191] = 0.0;
   out_6259423772009568262[192] = 0.0;
   out_6259423772009568262[193] = 0.0;
   out_6259423772009568262[194] = 0.0;
   out_6259423772009568262[195] = 0.0;
   out_6259423772009568262[196] = 0.0;
   out_6259423772009568262[197] = 0.0;
   out_6259423772009568262[198] = 0.0;
   out_6259423772009568262[199] = 0.0;
   out_6259423772009568262[200] = 0.0;
   out_6259423772009568262[201] = 0.0;
   out_6259423772009568262[202] = 0.0;
   out_6259423772009568262[203] = 0.0;
   out_6259423772009568262[204] = 0.0;
   out_6259423772009568262[205] = 0.0;
   out_6259423772009568262[206] = 0.0;
   out_6259423772009568262[207] = 0.0;
   out_6259423772009568262[208] = 0.0;
   out_6259423772009568262[209] = 1.0;
   out_6259423772009568262[210] = 0.0;
   out_6259423772009568262[211] = 0.0;
   out_6259423772009568262[212] = 0.0;
   out_6259423772009568262[213] = 0.0;
   out_6259423772009568262[214] = 0.0;
   out_6259423772009568262[215] = 0.0;
   out_6259423772009568262[216] = 0.0;
   out_6259423772009568262[217] = 0.0;
   out_6259423772009568262[218] = 0.0;
   out_6259423772009568262[219] = 0.0;
   out_6259423772009568262[220] = 0.0;
   out_6259423772009568262[221] = 0.0;
   out_6259423772009568262[222] = 0.0;
   out_6259423772009568262[223] = 0.0;
   out_6259423772009568262[224] = 0.0;
   out_6259423772009568262[225] = 0.0;
   out_6259423772009568262[226] = 0.0;
   out_6259423772009568262[227] = 0.0;
   out_6259423772009568262[228] = 1.0;
   out_6259423772009568262[229] = 0.0;
   out_6259423772009568262[230] = 0.0;
   out_6259423772009568262[231] = 0.0;
   out_6259423772009568262[232] = 0.0;
   out_6259423772009568262[233] = 0.0;
   out_6259423772009568262[234] = 0.0;
   out_6259423772009568262[235] = 0.0;
   out_6259423772009568262[236] = 0.0;
   out_6259423772009568262[237] = 0.0;
   out_6259423772009568262[238] = 0.0;
   out_6259423772009568262[239] = 0.0;
   out_6259423772009568262[240] = 0.0;
   out_6259423772009568262[241] = 0.0;
   out_6259423772009568262[242] = 0.0;
   out_6259423772009568262[243] = 0.0;
   out_6259423772009568262[244] = 0.0;
   out_6259423772009568262[245] = 0.0;
   out_6259423772009568262[246] = 0.0;
   out_6259423772009568262[247] = 1.0;
   out_6259423772009568262[248] = 0.0;
   out_6259423772009568262[249] = 0.0;
   out_6259423772009568262[250] = 0.0;
   out_6259423772009568262[251] = 0.0;
   out_6259423772009568262[252] = 0.0;
   out_6259423772009568262[253] = 0.0;
   out_6259423772009568262[254] = 0.0;
   out_6259423772009568262[255] = 0.0;
   out_6259423772009568262[256] = 0.0;
   out_6259423772009568262[257] = 0.0;
   out_6259423772009568262[258] = 0.0;
   out_6259423772009568262[259] = 0.0;
   out_6259423772009568262[260] = 0.0;
   out_6259423772009568262[261] = 0.0;
   out_6259423772009568262[262] = 0.0;
   out_6259423772009568262[263] = 0.0;
   out_6259423772009568262[264] = 0.0;
   out_6259423772009568262[265] = 0.0;
   out_6259423772009568262[266] = 1.0;
   out_6259423772009568262[267] = 0.0;
   out_6259423772009568262[268] = 0.0;
   out_6259423772009568262[269] = 0.0;
   out_6259423772009568262[270] = 0.0;
   out_6259423772009568262[271] = 0.0;
   out_6259423772009568262[272] = 0.0;
   out_6259423772009568262[273] = 0.0;
   out_6259423772009568262[274] = 0.0;
   out_6259423772009568262[275] = 0.0;
   out_6259423772009568262[276] = 0.0;
   out_6259423772009568262[277] = 0.0;
   out_6259423772009568262[278] = 0.0;
   out_6259423772009568262[279] = 0.0;
   out_6259423772009568262[280] = 0.0;
   out_6259423772009568262[281] = 0.0;
   out_6259423772009568262[282] = 0.0;
   out_6259423772009568262[283] = 0.0;
   out_6259423772009568262[284] = 0.0;
   out_6259423772009568262[285] = 1.0;
   out_6259423772009568262[286] = 0.0;
   out_6259423772009568262[287] = 0.0;
   out_6259423772009568262[288] = 0.0;
   out_6259423772009568262[289] = 0.0;
   out_6259423772009568262[290] = 0.0;
   out_6259423772009568262[291] = 0.0;
   out_6259423772009568262[292] = 0.0;
   out_6259423772009568262[293] = 0.0;
   out_6259423772009568262[294] = 0.0;
   out_6259423772009568262[295] = 0.0;
   out_6259423772009568262[296] = 0.0;
   out_6259423772009568262[297] = 0.0;
   out_6259423772009568262[298] = 0.0;
   out_6259423772009568262[299] = 0.0;
   out_6259423772009568262[300] = 0.0;
   out_6259423772009568262[301] = 0.0;
   out_6259423772009568262[302] = 0.0;
   out_6259423772009568262[303] = 0.0;
   out_6259423772009568262[304] = 1.0;
   out_6259423772009568262[305] = 0.0;
   out_6259423772009568262[306] = 0.0;
   out_6259423772009568262[307] = 0.0;
   out_6259423772009568262[308] = 0.0;
   out_6259423772009568262[309] = 0.0;
   out_6259423772009568262[310] = 0.0;
   out_6259423772009568262[311] = 0.0;
   out_6259423772009568262[312] = 0.0;
   out_6259423772009568262[313] = 0.0;
   out_6259423772009568262[314] = 0.0;
   out_6259423772009568262[315] = 0.0;
   out_6259423772009568262[316] = 0.0;
   out_6259423772009568262[317] = 0.0;
   out_6259423772009568262[318] = 0.0;
   out_6259423772009568262[319] = 0.0;
   out_6259423772009568262[320] = 0.0;
   out_6259423772009568262[321] = 0.0;
   out_6259423772009568262[322] = 0.0;
   out_6259423772009568262[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_855366903388822681) {
   out_855366903388822681[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_855366903388822681[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_855366903388822681[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_855366903388822681[3] = dt*state[12] + state[3];
   out_855366903388822681[4] = dt*state[13] + state[4];
   out_855366903388822681[5] = dt*state[14] + state[5];
   out_855366903388822681[6] = state[6];
   out_855366903388822681[7] = state[7];
   out_855366903388822681[8] = state[8];
   out_855366903388822681[9] = state[9];
   out_855366903388822681[10] = state[10];
   out_855366903388822681[11] = state[11];
   out_855366903388822681[12] = state[12];
   out_855366903388822681[13] = state[13];
   out_855366903388822681[14] = state[14];
   out_855366903388822681[15] = state[15];
   out_855366903388822681[16] = state[16];
   out_855366903388822681[17] = state[17];
}
void F_fun(double *state, double dt, double *out_1978214635701427629) {
   out_1978214635701427629[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1978214635701427629[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1978214635701427629[2] = 0;
   out_1978214635701427629[3] = 0;
   out_1978214635701427629[4] = 0;
   out_1978214635701427629[5] = 0;
   out_1978214635701427629[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1978214635701427629[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1978214635701427629[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1978214635701427629[9] = 0;
   out_1978214635701427629[10] = 0;
   out_1978214635701427629[11] = 0;
   out_1978214635701427629[12] = 0;
   out_1978214635701427629[13] = 0;
   out_1978214635701427629[14] = 0;
   out_1978214635701427629[15] = 0;
   out_1978214635701427629[16] = 0;
   out_1978214635701427629[17] = 0;
   out_1978214635701427629[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1978214635701427629[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1978214635701427629[20] = 0;
   out_1978214635701427629[21] = 0;
   out_1978214635701427629[22] = 0;
   out_1978214635701427629[23] = 0;
   out_1978214635701427629[24] = 0;
   out_1978214635701427629[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1978214635701427629[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1978214635701427629[27] = 0;
   out_1978214635701427629[28] = 0;
   out_1978214635701427629[29] = 0;
   out_1978214635701427629[30] = 0;
   out_1978214635701427629[31] = 0;
   out_1978214635701427629[32] = 0;
   out_1978214635701427629[33] = 0;
   out_1978214635701427629[34] = 0;
   out_1978214635701427629[35] = 0;
   out_1978214635701427629[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1978214635701427629[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1978214635701427629[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1978214635701427629[39] = 0;
   out_1978214635701427629[40] = 0;
   out_1978214635701427629[41] = 0;
   out_1978214635701427629[42] = 0;
   out_1978214635701427629[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1978214635701427629[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1978214635701427629[45] = 0;
   out_1978214635701427629[46] = 0;
   out_1978214635701427629[47] = 0;
   out_1978214635701427629[48] = 0;
   out_1978214635701427629[49] = 0;
   out_1978214635701427629[50] = 0;
   out_1978214635701427629[51] = 0;
   out_1978214635701427629[52] = 0;
   out_1978214635701427629[53] = 0;
   out_1978214635701427629[54] = 0;
   out_1978214635701427629[55] = 0;
   out_1978214635701427629[56] = 0;
   out_1978214635701427629[57] = 1;
   out_1978214635701427629[58] = 0;
   out_1978214635701427629[59] = 0;
   out_1978214635701427629[60] = 0;
   out_1978214635701427629[61] = 0;
   out_1978214635701427629[62] = 0;
   out_1978214635701427629[63] = 0;
   out_1978214635701427629[64] = 0;
   out_1978214635701427629[65] = 0;
   out_1978214635701427629[66] = dt;
   out_1978214635701427629[67] = 0;
   out_1978214635701427629[68] = 0;
   out_1978214635701427629[69] = 0;
   out_1978214635701427629[70] = 0;
   out_1978214635701427629[71] = 0;
   out_1978214635701427629[72] = 0;
   out_1978214635701427629[73] = 0;
   out_1978214635701427629[74] = 0;
   out_1978214635701427629[75] = 0;
   out_1978214635701427629[76] = 1;
   out_1978214635701427629[77] = 0;
   out_1978214635701427629[78] = 0;
   out_1978214635701427629[79] = 0;
   out_1978214635701427629[80] = 0;
   out_1978214635701427629[81] = 0;
   out_1978214635701427629[82] = 0;
   out_1978214635701427629[83] = 0;
   out_1978214635701427629[84] = 0;
   out_1978214635701427629[85] = dt;
   out_1978214635701427629[86] = 0;
   out_1978214635701427629[87] = 0;
   out_1978214635701427629[88] = 0;
   out_1978214635701427629[89] = 0;
   out_1978214635701427629[90] = 0;
   out_1978214635701427629[91] = 0;
   out_1978214635701427629[92] = 0;
   out_1978214635701427629[93] = 0;
   out_1978214635701427629[94] = 0;
   out_1978214635701427629[95] = 1;
   out_1978214635701427629[96] = 0;
   out_1978214635701427629[97] = 0;
   out_1978214635701427629[98] = 0;
   out_1978214635701427629[99] = 0;
   out_1978214635701427629[100] = 0;
   out_1978214635701427629[101] = 0;
   out_1978214635701427629[102] = 0;
   out_1978214635701427629[103] = 0;
   out_1978214635701427629[104] = dt;
   out_1978214635701427629[105] = 0;
   out_1978214635701427629[106] = 0;
   out_1978214635701427629[107] = 0;
   out_1978214635701427629[108] = 0;
   out_1978214635701427629[109] = 0;
   out_1978214635701427629[110] = 0;
   out_1978214635701427629[111] = 0;
   out_1978214635701427629[112] = 0;
   out_1978214635701427629[113] = 0;
   out_1978214635701427629[114] = 1;
   out_1978214635701427629[115] = 0;
   out_1978214635701427629[116] = 0;
   out_1978214635701427629[117] = 0;
   out_1978214635701427629[118] = 0;
   out_1978214635701427629[119] = 0;
   out_1978214635701427629[120] = 0;
   out_1978214635701427629[121] = 0;
   out_1978214635701427629[122] = 0;
   out_1978214635701427629[123] = 0;
   out_1978214635701427629[124] = 0;
   out_1978214635701427629[125] = 0;
   out_1978214635701427629[126] = 0;
   out_1978214635701427629[127] = 0;
   out_1978214635701427629[128] = 0;
   out_1978214635701427629[129] = 0;
   out_1978214635701427629[130] = 0;
   out_1978214635701427629[131] = 0;
   out_1978214635701427629[132] = 0;
   out_1978214635701427629[133] = 1;
   out_1978214635701427629[134] = 0;
   out_1978214635701427629[135] = 0;
   out_1978214635701427629[136] = 0;
   out_1978214635701427629[137] = 0;
   out_1978214635701427629[138] = 0;
   out_1978214635701427629[139] = 0;
   out_1978214635701427629[140] = 0;
   out_1978214635701427629[141] = 0;
   out_1978214635701427629[142] = 0;
   out_1978214635701427629[143] = 0;
   out_1978214635701427629[144] = 0;
   out_1978214635701427629[145] = 0;
   out_1978214635701427629[146] = 0;
   out_1978214635701427629[147] = 0;
   out_1978214635701427629[148] = 0;
   out_1978214635701427629[149] = 0;
   out_1978214635701427629[150] = 0;
   out_1978214635701427629[151] = 0;
   out_1978214635701427629[152] = 1;
   out_1978214635701427629[153] = 0;
   out_1978214635701427629[154] = 0;
   out_1978214635701427629[155] = 0;
   out_1978214635701427629[156] = 0;
   out_1978214635701427629[157] = 0;
   out_1978214635701427629[158] = 0;
   out_1978214635701427629[159] = 0;
   out_1978214635701427629[160] = 0;
   out_1978214635701427629[161] = 0;
   out_1978214635701427629[162] = 0;
   out_1978214635701427629[163] = 0;
   out_1978214635701427629[164] = 0;
   out_1978214635701427629[165] = 0;
   out_1978214635701427629[166] = 0;
   out_1978214635701427629[167] = 0;
   out_1978214635701427629[168] = 0;
   out_1978214635701427629[169] = 0;
   out_1978214635701427629[170] = 0;
   out_1978214635701427629[171] = 1;
   out_1978214635701427629[172] = 0;
   out_1978214635701427629[173] = 0;
   out_1978214635701427629[174] = 0;
   out_1978214635701427629[175] = 0;
   out_1978214635701427629[176] = 0;
   out_1978214635701427629[177] = 0;
   out_1978214635701427629[178] = 0;
   out_1978214635701427629[179] = 0;
   out_1978214635701427629[180] = 0;
   out_1978214635701427629[181] = 0;
   out_1978214635701427629[182] = 0;
   out_1978214635701427629[183] = 0;
   out_1978214635701427629[184] = 0;
   out_1978214635701427629[185] = 0;
   out_1978214635701427629[186] = 0;
   out_1978214635701427629[187] = 0;
   out_1978214635701427629[188] = 0;
   out_1978214635701427629[189] = 0;
   out_1978214635701427629[190] = 1;
   out_1978214635701427629[191] = 0;
   out_1978214635701427629[192] = 0;
   out_1978214635701427629[193] = 0;
   out_1978214635701427629[194] = 0;
   out_1978214635701427629[195] = 0;
   out_1978214635701427629[196] = 0;
   out_1978214635701427629[197] = 0;
   out_1978214635701427629[198] = 0;
   out_1978214635701427629[199] = 0;
   out_1978214635701427629[200] = 0;
   out_1978214635701427629[201] = 0;
   out_1978214635701427629[202] = 0;
   out_1978214635701427629[203] = 0;
   out_1978214635701427629[204] = 0;
   out_1978214635701427629[205] = 0;
   out_1978214635701427629[206] = 0;
   out_1978214635701427629[207] = 0;
   out_1978214635701427629[208] = 0;
   out_1978214635701427629[209] = 1;
   out_1978214635701427629[210] = 0;
   out_1978214635701427629[211] = 0;
   out_1978214635701427629[212] = 0;
   out_1978214635701427629[213] = 0;
   out_1978214635701427629[214] = 0;
   out_1978214635701427629[215] = 0;
   out_1978214635701427629[216] = 0;
   out_1978214635701427629[217] = 0;
   out_1978214635701427629[218] = 0;
   out_1978214635701427629[219] = 0;
   out_1978214635701427629[220] = 0;
   out_1978214635701427629[221] = 0;
   out_1978214635701427629[222] = 0;
   out_1978214635701427629[223] = 0;
   out_1978214635701427629[224] = 0;
   out_1978214635701427629[225] = 0;
   out_1978214635701427629[226] = 0;
   out_1978214635701427629[227] = 0;
   out_1978214635701427629[228] = 1;
   out_1978214635701427629[229] = 0;
   out_1978214635701427629[230] = 0;
   out_1978214635701427629[231] = 0;
   out_1978214635701427629[232] = 0;
   out_1978214635701427629[233] = 0;
   out_1978214635701427629[234] = 0;
   out_1978214635701427629[235] = 0;
   out_1978214635701427629[236] = 0;
   out_1978214635701427629[237] = 0;
   out_1978214635701427629[238] = 0;
   out_1978214635701427629[239] = 0;
   out_1978214635701427629[240] = 0;
   out_1978214635701427629[241] = 0;
   out_1978214635701427629[242] = 0;
   out_1978214635701427629[243] = 0;
   out_1978214635701427629[244] = 0;
   out_1978214635701427629[245] = 0;
   out_1978214635701427629[246] = 0;
   out_1978214635701427629[247] = 1;
   out_1978214635701427629[248] = 0;
   out_1978214635701427629[249] = 0;
   out_1978214635701427629[250] = 0;
   out_1978214635701427629[251] = 0;
   out_1978214635701427629[252] = 0;
   out_1978214635701427629[253] = 0;
   out_1978214635701427629[254] = 0;
   out_1978214635701427629[255] = 0;
   out_1978214635701427629[256] = 0;
   out_1978214635701427629[257] = 0;
   out_1978214635701427629[258] = 0;
   out_1978214635701427629[259] = 0;
   out_1978214635701427629[260] = 0;
   out_1978214635701427629[261] = 0;
   out_1978214635701427629[262] = 0;
   out_1978214635701427629[263] = 0;
   out_1978214635701427629[264] = 0;
   out_1978214635701427629[265] = 0;
   out_1978214635701427629[266] = 1;
   out_1978214635701427629[267] = 0;
   out_1978214635701427629[268] = 0;
   out_1978214635701427629[269] = 0;
   out_1978214635701427629[270] = 0;
   out_1978214635701427629[271] = 0;
   out_1978214635701427629[272] = 0;
   out_1978214635701427629[273] = 0;
   out_1978214635701427629[274] = 0;
   out_1978214635701427629[275] = 0;
   out_1978214635701427629[276] = 0;
   out_1978214635701427629[277] = 0;
   out_1978214635701427629[278] = 0;
   out_1978214635701427629[279] = 0;
   out_1978214635701427629[280] = 0;
   out_1978214635701427629[281] = 0;
   out_1978214635701427629[282] = 0;
   out_1978214635701427629[283] = 0;
   out_1978214635701427629[284] = 0;
   out_1978214635701427629[285] = 1;
   out_1978214635701427629[286] = 0;
   out_1978214635701427629[287] = 0;
   out_1978214635701427629[288] = 0;
   out_1978214635701427629[289] = 0;
   out_1978214635701427629[290] = 0;
   out_1978214635701427629[291] = 0;
   out_1978214635701427629[292] = 0;
   out_1978214635701427629[293] = 0;
   out_1978214635701427629[294] = 0;
   out_1978214635701427629[295] = 0;
   out_1978214635701427629[296] = 0;
   out_1978214635701427629[297] = 0;
   out_1978214635701427629[298] = 0;
   out_1978214635701427629[299] = 0;
   out_1978214635701427629[300] = 0;
   out_1978214635701427629[301] = 0;
   out_1978214635701427629[302] = 0;
   out_1978214635701427629[303] = 0;
   out_1978214635701427629[304] = 1;
   out_1978214635701427629[305] = 0;
   out_1978214635701427629[306] = 0;
   out_1978214635701427629[307] = 0;
   out_1978214635701427629[308] = 0;
   out_1978214635701427629[309] = 0;
   out_1978214635701427629[310] = 0;
   out_1978214635701427629[311] = 0;
   out_1978214635701427629[312] = 0;
   out_1978214635701427629[313] = 0;
   out_1978214635701427629[314] = 0;
   out_1978214635701427629[315] = 0;
   out_1978214635701427629[316] = 0;
   out_1978214635701427629[317] = 0;
   out_1978214635701427629[318] = 0;
   out_1978214635701427629[319] = 0;
   out_1978214635701427629[320] = 0;
   out_1978214635701427629[321] = 0;
   out_1978214635701427629[322] = 0;
   out_1978214635701427629[323] = 1;
}
void h_4(double *state, double *unused, double *out_4297907286096878653) {
   out_4297907286096878653[0] = state[6] + state[9];
   out_4297907286096878653[1] = state[7] + state[10];
   out_4297907286096878653[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8079122497915865123) {
   out_8079122497915865123[0] = 0;
   out_8079122497915865123[1] = 0;
   out_8079122497915865123[2] = 0;
   out_8079122497915865123[3] = 0;
   out_8079122497915865123[4] = 0;
   out_8079122497915865123[5] = 0;
   out_8079122497915865123[6] = 1;
   out_8079122497915865123[7] = 0;
   out_8079122497915865123[8] = 0;
   out_8079122497915865123[9] = 1;
   out_8079122497915865123[10] = 0;
   out_8079122497915865123[11] = 0;
   out_8079122497915865123[12] = 0;
   out_8079122497915865123[13] = 0;
   out_8079122497915865123[14] = 0;
   out_8079122497915865123[15] = 0;
   out_8079122497915865123[16] = 0;
   out_8079122497915865123[17] = 0;
   out_8079122497915865123[18] = 0;
   out_8079122497915865123[19] = 0;
   out_8079122497915865123[20] = 0;
   out_8079122497915865123[21] = 0;
   out_8079122497915865123[22] = 0;
   out_8079122497915865123[23] = 0;
   out_8079122497915865123[24] = 0;
   out_8079122497915865123[25] = 1;
   out_8079122497915865123[26] = 0;
   out_8079122497915865123[27] = 0;
   out_8079122497915865123[28] = 1;
   out_8079122497915865123[29] = 0;
   out_8079122497915865123[30] = 0;
   out_8079122497915865123[31] = 0;
   out_8079122497915865123[32] = 0;
   out_8079122497915865123[33] = 0;
   out_8079122497915865123[34] = 0;
   out_8079122497915865123[35] = 0;
   out_8079122497915865123[36] = 0;
   out_8079122497915865123[37] = 0;
   out_8079122497915865123[38] = 0;
   out_8079122497915865123[39] = 0;
   out_8079122497915865123[40] = 0;
   out_8079122497915865123[41] = 0;
   out_8079122497915865123[42] = 0;
   out_8079122497915865123[43] = 0;
   out_8079122497915865123[44] = 1;
   out_8079122497915865123[45] = 0;
   out_8079122497915865123[46] = 0;
   out_8079122497915865123[47] = 1;
   out_8079122497915865123[48] = 0;
   out_8079122497915865123[49] = 0;
   out_8079122497915865123[50] = 0;
   out_8079122497915865123[51] = 0;
   out_8079122497915865123[52] = 0;
   out_8079122497915865123[53] = 0;
}
void h_10(double *state, double *unused, double *out_2075957019235364681) {
   out_2075957019235364681[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_2075957019235364681[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_2075957019235364681[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4849572450209365182) {
   out_4849572450209365182[0] = 0;
   out_4849572450209365182[1] = 9.8100000000000005*cos(state[1]);
   out_4849572450209365182[2] = 0;
   out_4849572450209365182[3] = 0;
   out_4849572450209365182[4] = -state[8];
   out_4849572450209365182[5] = state[7];
   out_4849572450209365182[6] = 0;
   out_4849572450209365182[7] = state[5];
   out_4849572450209365182[8] = -state[4];
   out_4849572450209365182[9] = 0;
   out_4849572450209365182[10] = 0;
   out_4849572450209365182[11] = 0;
   out_4849572450209365182[12] = 1;
   out_4849572450209365182[13] = 0;
   out_4849572450209365182[14] = 0;
   out_4849572450209365182[15] = 1;
   out_4849572450209365182[16] = 0;
   out_4849572450209365182[17] = 0;
   out_4849572450209365182[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4849572450209365182[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4849572450209365182[20] = 0;
   out_4849572450209365182[21] = state[8];
   out_4849572450209365182[22] = 0;
   out_4849572450209365182[23] = -state[6];
   out_4849572450209365182[24] = -state[5];
   out_4849572450209365182[25] = 0;
   out_4849572450209365182[26] = state[3];
   out_4849572450209365182[27] = 0;
   out_4849572450209365182[28] = 0;
   out_4849572450209365182[29] = 0;
   out_4849572450209365182[30] = 0;
   out_4849572450209365182[31] = 1;
   out_4849572450209365182[32] = 0;
   out_4849572450209365182[33] = 0;
   out_4849572450209365182[34] = 1;
   out_4849572450209365182[35] = 0;
   out_4849572450209365182[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4849572450209365182[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4849572450209365182[38] = 0;
   out_4849572450209365182[39] = -state[7];
   out_4849572450209365182[40] = state[6];
   out_4849572450209365182[41] = 0;
   out_4849572450209365182[42] = state[4];
   out_4849572450209365182[43] = -state[3];
   out_4849572450209365182[44] = 0;
   out_4849572450209365182[45] = 0;
   out_4849572450209365182[46] = 0;
   out_4849572450209365182[47] = 0;
   out_4849572450209365182[48] = 0;
   out_4849572450209365182[49] = 0;
   out_4849572450209365182[50] = 1;
   out_4849572450209365182[51] = 0;
   out_4849572450209365182[52] = 0;
   out_4849572450209365182[53] = 1;
}
void h_13(double *state, double *unused, double *out_3557575460249098873) {
   out_3557575460249098873[0] = state[3];
   out_3557575460249098873[1] = state[4];
   out_3557575460249098873[2] = state[5];
}
void H_13(double *state, double *unused, double *out_4866848672583532322) {
   out_4866848672583532322[0] = 0;
   out_4866848672583532322[1] = 0;
   out_4866848672583532322[2] = 0;
   out_4866848672583532322[3] = 1;
   out_4866848672583532322[4] = 0;
   out_4866848672583532322[5] = 0;
   out_4866848672583532322[6] = 0;
   out_4866848672583532322[7] = 0;
   out_4866848672583532322[8] = 0;
   out_4866848672583532322[9] = 0;
   out_4866848672583532322[10] = 0;
   out_4866848672583532322[11] = 0;
   out_4866848672583532322[12] = 0;
   out_4866848672583532322[13] = 0;
   out_4866848672583532322[14] = 0;
   out_4866848672583532322[15] = 0;
   out_4866848672583532322[16] = 0;
   out_4866848672583532322[17] = 0;
   out_4866848672583532322[18] = 0;
   out_4866848672583532322[19] = 0;
   out_4866848672583532322[20] = 0;
   out_4866848672583532322[21] = 0;
   out_4866848672583532322[22] = 1;
   out_4866848672583532322[23] = 0;
   out_4866848672583532322[24] = 0;
   out_4866848672583532322[25] = 0;
   out_4866848672583532322[26] = 0;
   out_4866848672583532322[27] = 0;
   out_4866848672583532322[28] = 0;
   out_4866848672583532322[29] = 0;
   out_4866848672583532322[30] = 0;
   out_4866848672583532322[31] = 0;
   out_4866848672583532322[32] = 0;
   out_4866848672583532322[33] = 0;
   out_4866848672583532322[34] = 0;
   out_4866848672583532322[35] = 0;
   out_4866848672583532322[36] = 0;
   out_4866848672583532322[37] = 0;
   out_4866848672583532322[38] = 0;
   out_4866848672583532322[39] = 0;
   out_4866848672583532322[40] = 0;
   out_4866848672583532322[41] = 1;
   out_4866848672583532322[42] = 0;
   out_4866848672583532322[43] = 0;
   out_4866848672583532322[44] = 0;
   out_4866848672583532322[45] = 0;
   out_4866848672583532322[46] = 0;
   out_4866848672583532322[47] = 0;
   out_4866848672583532322[48] = 0;
   out_4866848672583532322[49] = 0;
   out_4866848672583532322[50] = 0;
   out_4866848672583532322[51] = 0;
   out_4866848672583532322[52] = 0;
   out_4866848672583532322[53] = 0;
}
void h_14(double *state, double *unused, double *out_175200106668597994) {
   out_175200106668597994[0] = state[6];
   out_175200106668597994[1] = state[7];
   out_175200106668597994[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7284833143498314197) {
   out_7284833143498314197[0] = 0;
   out_7284833143498314197[1] = 0;
   out_7284833143498314197[2] = 0;
   out_7284833143498314197[3] = 0;
   out_7284833143498314197[4] = 0;
   out_7284833143498314197[5] = 0;
   out_7284833143498314197[6] = 1;
   out_7284833143498314197[7] = 0;
   out_7284833143498314197[8] = 0;
   out_7284833143498314197[9] = 0;
   out_7284833143498314197[10] = 0;
   out_7284833143498314197[11] = 0;
   out_7284833143498314197[12] = 0;
   out_7284833143498314197[13] = 0;
   out_7284833143498314197[14] = 0;
   out_7284833143498314197[15] = 0;
   out_7284833143498314197[16] = 0;
   out_7284833143498314197[17] = 0;
   out_7284833143498314197[18] = 0;
   out_7284833143498314197[19] = 0;
   out_7284833143498314197[20] = 0;
   out_7284833143498314197[21] = 0;
   out_7284833143498314197[22] = 0;
   out_7284833143498314197[23] = 0;
   out_7284833143498314197[24] = 0;
   out_7284833143498314197[25] = 1;
   out_7284833143498314197[26] = 0;
   out_7284833143498314197[27] = 0;
   out_7284833143498314197[28] = 0;
   out_7284833143498314197[29] = 0;
   out_7284833143498314197[30] = 0;
   out_7284833143498314197[31] = 0;
   out_7284833143498314197[32] = 0;
   out_7284833143498314197[33] = 0;
   out_7284833143498314197[34] = 0;
   out_7284833143498314197[35] = 0;
   out_7284833143498314197[36] = 0;
   out_7284833143498314197[37] = 0;
   out_7284833143498314197[38] = 0;
   out_7284833143498314197[39] = 0;
   out_7284833143498314197[40] = 0;
   out_7284833143498314197[41] = 0;
   out_7284833143498314197[42] = 0;
   out_7284833143498314197[43] = 0;
   out_7284833143498314197[44] = 1;
   out_7284833143498314197[45] = 0;
   out_7284833143498314197[46] = 0;
   out_7284833143498314197[47] = 0;
   out_7284833143498314197[48] = 0;
   out_7284833143498314197[49] = 0;
   out_7284833143498314197[50] = 0;
   out_7284833143498314197[51] = 0;
   out_7284833143498314197[52] = 0;
   out_7284833143498314197[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_581108018479819489) {
  err_fun(nom_x, delta_x, out_581108018479819489);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7407620403679899755) {
  inv_err_fun(nom_x, true_x, out_7407620403679899755);
}
void pose_H_mod_fun(double *state, double *out_6259423772009568262) {
  H_mod_fun(state, out_6259423772009568262);
}
void pose_f_fun(double *state, double dt, double *out_855366903388822681) {
  f_fun(state,  dt, out_855366903388822681);
}
void pose_F_fun(double *state, double dt, double *out_1978214635701427629) {
  F_fun(state,  dt, out_1978214635701427629);
}
void pose_h_4(double *state, double *unused, double *out_4297907286096878653) {
  h_4(state, unused, out_4297907286096878653);
}
void pose_H_4(double *state, double *unused, double *out_8079122497915865123) {
  H_4(state, unused, out_8079122497915865123);
}
void pose_h_10(double *state, double *unused, double *out_2075957019235364681) {
  h_10(state, unused, out_2075957019235364681);
}
void pose_H_10(double *state, double *unused, double *out_4849572450209365182) {
  H_10(state, unused, out_4849572450209365182);
}
void pose_h_13(double *state, double *unused, double *out_3557575460249098873) {
  h_13(state, unused, out_3557575460249098873);
}
void pose_H_13(double *state, double *unused, double *out_4866848672583532322) {
  H_13(state, unused, out_4866848672583532322);
}
void pose_h_14(double *state, double *unused, double *out_175200106668597994) {
  h_14(state, unused, out_175200106668597994);
}
void pose_H_14(double *state, double *unused, double *out_7284833143498314197) {
  H_14(state, unused, out_7284833143498314197);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
