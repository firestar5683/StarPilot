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
void err_fun(double *nom_x, double *delta_x, double *out_486750963754107954) {
   out_486750963754107954[0] = delta_x[0] + nom_x[0];
   out_486750963754107954[1] = delta_x[1] + nom_x[1];
   out_486750963754107954[2] = delta_x[2] + nom_x[2];
   out_486750963754107954[3] = delta_x[3] + nom_x[3];
   out_486750963754107954[4] = delta_x[4] + nom_x[4];
   out_486750963754107954[5] = delta_x[5] + nom_x[5];
   out_486750963754107954[6] = delta_x[6] + nom_x[6];
   out_486750963754107954[7] = delta_x[7] + nom_x[7];
   out_486750963754107954[8] = delta_x[8] + nom_x[8];
   out_486750963754107954[9] = delta_x[9] + nom_x[9];
   out_486750963754107954[10] = delta_x[10] + nom_x[10];
   out_486750963754107954[11] = delta_x[11] + nom_x[11];
   out_486750963754107954[12] = delta_x[12] + nom_x[12];
   out_486750963754107954[13] = delta_x[13] + nom_x[13];
   out_486750963754107954[14] = delta_x[14] + nom_x[14];
   out_486750963754107954[15] = delta_x[15] + nom_x[15];
   out_486750963754107954[16] = delta_x[16] + nom_x[16];
   out_486750963754107954[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_1555487183493314770) {
   out_1555487183493314770[0] = -nom_x[0] + true_x[0];
   out_1555487183493314770[1] = -nom_x[1] + true_x[1];
   out_1555487183493314770[2] = -nom_x[2] + true_x[2];
   out_1555487183493314770[3] = -nom_x[3] + true_x[3];
   out_1555487183493314770[4] = -nom_x[4] + true_x[4];
   out_1555487183493314770[5] = -nom_x[5] + true_x[5];
   out_1555487183493314770[6] = -nom_x[6] + true_x[6];
   out_1555487183493314770[7] = -nom_x[7] + true_x[7];
   out_1555487183493314770[8] = -nom_x[8] + true_x[8];
   out_1555487183493314770[9] = -nom_x[9] + true_x[9];
   out_1555487183493314770[10] = -nom_x[10] + true_x[10];
   out_1555487183493314770[11] = -nom_x[11] + true_x[11];
   out_1555487183493314770[12] = -nom_x[12] + true_x[12];
   out_1555487183493314770[13] = -nom_x[13] + true_x[13];
   out_1555487183493314770[14] = -nom_x[14] + true_x[14];
   out_1555487183493314770[15] = -nom_x[15] + true_x[15];
   out_1555487183493314770[16] = -nom_x[16] + true_x[16];
   out_1555487183493314770[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_2668724034635220264) {
   out_2668724034635220264[0] = 1.0;
   out_2668724034635220264[1] = 0.0;
   out_2668724034635220264[2] = 0.0;
   out_2668724034635220264[3] = 0.0;
   out_2668724034635220264[4] = 0.0;
   out_2668724034635220264[5] = 0.0;
   out_2668724034635220264[6] = 0.0;
   out_2668724034635220264[7] = 0.0;
   out_2668724034635220264[8] = 0.0;
   out_2668724034635220264[9] = 0.0;
   out_2668724034635220264[10] = 0.0;
   out_2668724034635220264[11] = 0.0;
   out_2668724034635220264[12] = 0.0;
   out_2668724034635220264[13] = 0.0;
   out_2668724034635220264[14] = 0.0;
   out_2668724034635220264[15] = 0.0;
   out_2668724034635220264[16] = 0.0;
   out_2668724034635220264[17] = 0.0;
   out_2668724034635220264[18] = 0.0;
   out_2668724034635220264[19] = 1.0;
   out_2668724034635220264[20] = 0.0;
   out_2668724034635220264[21] = 0.0;
   out_2668724034635220264[22] = 0.0;
   out_2668724034635220264[23] = 0.0;
   out_2668724034635220264[24] = 0.0;
   out_2668724034635220264[25] = 0.0;
   out_2668724034635220264[26] = 0.0;
   out_2668724034635220264[27] = 0.0;
   out_2668724034635220264[28] = 0.0;
   out_2668724034635220264[29] = 0.0;
   out_2668724034635220264[30] = 0.0;
   out_2668724034635220264[31] = 0.0;
   out_2668724034635220264[32] = 0.0;
   out_2668724034635220264[33] = 0.0;
   out_2668724034635220264[34] = 0.0;
   out_2668724034635220264[35] = 0.0;
   out_2668724034635220264[36] = 0.0;
   out_2668724034635220264[37] = 0.0;
   out_2668724034635220264[38] = 1.0;
   out_2668724034635220264[39] = 0.0;
   out_2668724034635220264[40] = 0.0;
   out_2668724034635220264[41] = 0.0;
   out_2668724034635220264[42] = 0.0;
   out_2668724034635220264[43] = 0.0;
   out_2668724034635220264[44] = 0.0;
   out_2668724034635220264[45] = 0.0;
   out_2668724034635220264[46] = 0.0;
   out_2668724034635220264[47] = 0.0;
   out_2668724034635220264[48] = 0.0;
   out_2668724034635220264[49] = 0.0;
   out_2668724034635220264[50] = 0.0;
   out_2668724034635220264[51] = 0.0;
   out_2668724034635220264[52] = 0.0;
   out_2668724034635220264[53] = 0.0;
   out_2668724034635220264[54] = 0.0;
   out_2668724034635220264[55] = 0.0;
   out_2668724034635220264[56] = 0.0;
   out_2668724034635220264[57] = 1.0;
   out_2668724034635220264[58] = 0.0;
   out_2668724034635220264[59] = 0.0;
   out_2668724034635220264[60] = 0.0;
   out_2668724034635220264[61] = 0.0;
   out_2668724034635220264[62] = 0.0;
   out_2668724034635220264[63] = 0.0;
   out_2668724034635220264[64] = 0.0;
   out_2668724034635220264[65] = 0.0;
   out_2668724034635220264[66] = 0.0;
   out_2668724034635220264[67] = 0.0;
   out_2668724034635220264[68] = 0.0;
   out_2668724034635220264[69] = 0.0;
   out_2668724034635220264[70] = 0.0;
   out_2668724034635220264[71] = 0.0;
   out_2668724034635220264[72] = 0.0;
   out_2668724034635220264[73] = 0.0;
   out_2668724034635220264[74] = 0.0;
   out_2668724034635220264[75] = 0.0;
   out_2668724034635220264[76] = 1.0;
   out_2668724034635220264[77] = 0.0;
   out_2668724034635220264[78] = 0.0;
   out_2668724034635220264[79] = 0.0;
   out_2668724034635220264[80] = 0.0;
   out_2668724034635220264[81] = 0.0;
   out_2668724034635220264[82] = 0.0;
   out_2668724034635220264[83] = 0.0;
   out_2668724034635220264[84] = 0.0;
   out_2668724034635220264[85] = 0.0;
   out_2668724034635220264[86] = 0.0;
   out_2668724034635220264[87] = 0.0;
   out_2668724034635220264[88] = 0.0;
   out_2668724034635220264[89] = 0.0;
   out_2668724034635220264[90] = 0.0;
   out_2668724034635220264[91] = 0.0;
   out_2668724034635220264[92] = 0.0;
   out_2668724034635220264[93] = 0.0;
   out_2668724034635220264[94] = 0.0;
   out_2668724034635220264[95] = 1.0;
   out_2668724034635220264[96] = 0.0;
   out_2668724034635220264[97] = 0.0;
   out_2668724034635220264[98] = 0.0;
   out_2668724034635220264[99] = 0.0;
   out_2668724034635220264[100] = 0.0;
   out_2668724034635220264[101] = 0.0;
   out_2668724034635220264[102] = 0.0;
   out_2668724034635220264[103] = 0.0;
   out_2668724034635220264[104] = 0.0;
   out_2668724034635220264[105] = 0.0;
   out_2668724034635220264[106] = 0.0;
   out_2668724034635220264[107] = 0.0;
   out_2668724034635220264[108] = 0.0;
   out_2668724034635220264[109] = 0.0;
   out_2668724034635220264[110] = 0.0;
   out_2668724034635220264[111] = 0.0;
   out_2668724034635220264[112] = 0.0;
   out_2668724034635220264[113] = 0.0;
   out_2668724034635220264[114] = 1.0;
   out_2668724034635220264[115] = 0.0;
   out_2668724034635220264[116] = 0.0;
   out_2668724034635220264[117] = 0.0;
   out_2668724034635220264[118] = 0.0;
   out_2668724034635220264[119] = 0.0;
   out_2668724034635220264[120] = 0.0;
   out_2668724034635220264[121] = 0.0;
   out_2668724034635220264[122] = 0.0;
   out_2668724034635220264[123] = 0.0;
   out_2668724034635220264[124] = 0.0;
   out_2668724034635220264[125] = 0.0;
   out_2668724034635220264[126] = 0.0;
   out_2668724034635220264[127] = 0.0;
   out_2668724034635220264[128] = 0.0;
   out_2668724034635220264[129] = 0.0;
   out_2668724034635220264[130] = 0.0;
   out_2668724034635220264[131] = 0.0;
   out_2668724034635220264[132] = 0.0;
   out_2668724034635220264[133] = 1.0;
   out_2668724034635220264[134] = 0.0;
   out_2668724034635220264[135] = 0.0;
   out_2668724034635220264[136] = 0.0;
   out_2668724034635220264[137] = 0.0;
   out_2668724034635220264[138] = 0.0;
   out_2668724034635220264[139] = 0.0;
   out_2668724034635220264[140] = 0.0;
   out_2668724034635220264[141] = 0.0;
   out_2668724034635220264[142] = 0.0;
   out_2668724034635220264[143] = 0.0;
   out_2668724034635220264[144] = 0.0;
   out_2668724034635220264[145] = 0.0;
   out_2668724034635220264[146] = 0.0;
   out_2668724034635220264[147] = 0.0;
   out_2668724034635220264[148] = 0.0;
   out_2668724034635220264[149] = 0.0;
   out_2668724034635220264[150] = 0.0;
   out_2668724034635220264[151] = 0.0;
   out_2668724034635220264[152] = 1.0;
   out_2668724034635220264[153] = 0.0;
   out_2668724034635220264[154] = 0.0;
   out_2668724034635220264[155] = 0.0;
   out_2668724034635220264[156] = 0.0;
   out_2668724034635220264[157] = 0.0;
   out_2668724034635220264[158] = 0.0;
   out_2668724034635220264[159] = 0.0;
   out_2668724034635220264[160] = 0.0;
   out_2668724034635220264[161] = 0.0;
   out_2668724034635220264[162] = 0.0;
   out_2668724034635220264[163] = 0.0;
   out_2668724034635220264[164] = 0.0;
   out_2668724034635220264[165] = 0.0;
   out_2668724034635220264[166] = 0.0;
   out_2668724034635220264[167] = 0.0;
   out_2668724034635220264[168] = 0.0;
   out_2668724034635220264[169] = 0.0;
   out_2668724034635220264[170] = 0.0;
   out_2668724034635220264[171] = 1.0;
   out_2668724034635220264[172] = 0.0;
   out_2668724034635220264[173] = 0.0;
   out_2668724034635220264[174] = 0.0;
   out_2668724034635220264[175] = 0.0;
   out_2668724034635220264[176] = 0.0;
   out_2668724034635220264[177] = 0.0;
   out_2668724034635220264[178] = 0.0;
   out_2668724034635220264[179] = 0.0;
   out_2668724034635220264[180] = 0.0;
   out_2668724034635220264[181] = 0.0;
   out_2668724034635220264[182] = 0.0;
   out_2668724034635220264[183] = 0.0;
   out_2668724034635220264[184] = 0.0;
   out_2668724034635220264[185] = 0.0;
   out_2668724034635220264[186] = 0.0;
   out_2668724034635220264[187] = 0.0;
   out_2668724034635220264[188] = 0.0;
   out_2668724034635220264[189] = 0.0;
   out_2668724034635220264[190] = 1.0;
   out_2668724034635220264[191] = 0.0;
   out_2668724034635220264[192] = 0.0;
   out_2668724034635220264[193] = 0.0;
   out_2668724034635220264[194] = 0.0;
   out_2668724034635220264[195] = 0.0;
   out_2668724034635220264[196] = 0.0;
   out_2668724034635220264[197] = 0.0;
   out_2668724034635220264[198] = 0.0;
   out_2668724034635220264[199] = 0.0;
   out_2668724034635220264[200] = 0.0;
   out_2668724034635220264[201] = 0.0;
   out_2668724034635220264[202] = 0.0;
   out_2668724034635220264[203] = 0.0;
   out_2668724034635220264[204] = 0.0;
   out_2668724034635220264[205] = 0.0;
   out_2668724034635220264[206] = 0.0;
   out_2668724034635220264[207] = 0.0;
   out_2668724034635220264[208] = 0.0;
   out_2668724034635220264[209] = 1.0;
   out_2668724034635220264[210] = 0.0;
   out_2668724034635220264[211] = 0.0;
   out_2668724034635220264[212] = 0.0;
   out_2668724034635220264[213] = 0.0;
   out_2668724034635220264[214] = 0.0;
   out_2668724034635220264[215] = 0.0;
   out_2668724034635220264[216] = 0.0;
   out_2668724034635220264[217] = 0.0;
   out_2668724034635220264[218] = 0.0;
   out_2668724034635220264[219] = 0.0;
   out_2668724034635220264[220] = 0.0;
   out_2668724034635220264[221] = 0.0;
   out_2668724034635220264[222] = 0.0;
   out_2668724034635220264[223] = 0.0;
   out_2668724034635220264[224] = 0.0;
   out_2668724034635220264[225] = 0.0;
   out_2668724034635220264[226] = 0.0;
   out_2668724034635220264[227] = 0.0;
   out_2668724034635220264[228] = 1.0;
   out_2668724034635220264[229] = 0.0;
   out_2668724034635220264[230] = 0.0;
   out_2668724034635220264[231] = 0.0;
   out_2668724034635220264[232] = 0.0;
   out_2668724034635220264[233] = 0.0;
   out_2668724034635220264[234] = 0.0;
   out_2668724034635220264[235] = 0.0;
   out_2668724034635220264[236] = 0.0;
   out_2668724034635220264[237] = 0.0;
   out_2668724034635220264[238] = 0.0;
   out_2668724034635220264[239] = 0.0;
   out_2668724034635220264[240] = 0.0;
   out_2668724034635220264[241] = 0.0;
   out_2668724034635220264[242] = 0.0;
   out_2668724034635220264[243] = 0.0;
   out_2668724034635220264[244] = 0.0;
   out_2668724034635220264[245] = 0.0;
   out_2668724034635220264[246] = 0.0;
   out_2668724034635220264[247] = 1.0;
   out_2668724034635220264[248] = 0.0;
   out_2668724034635220264[249] = 0.0;
   out_2668724034635220264[250] = 0.0;
   out_2668724034635220264[251] = 0.0;
   out_2668724034635220264[252] = 0.0;
   out_2668724034635220264[253] = 0.0;
   out_2668724034635220264[254] = 0.0;
   out_2668724034635220264[255] = 0.0;
   out_2668724034635220264[256] = 0.0;
   out_2668724034635220264[257] = 0.0;
   out_2668724034635220264[258] = 0.0;
   out_2668724034635220264[259] = 0.0;
   out_2668724034635220264[260] = 0.0;
   out_2668724034635220264[261] = 0.0;
   out_2668724034635220264[262] = 0.0;
   out_2668724034635220264[263] = 0.0;
   out_2668724034635220264[264] = 0.0;
   out_2668724034635220264[265] = 0.0;
   out_2668724034635220264[266] = 1.0;
   out_2668724034635220264[267] = 0.0;
   out_2668724034635220264[268] = 0.0;
   out_2668724034635220264[269] = 0.0;
   out_2668724034635220264[270] = 0.0;
   out_2668724034635220264[271] = 0.0;
   out_2668724034635220264[272] = 0.0;
   out_2668724034635220264[273] = 0.0;
   out_2668724034635220264[274] = 0.0;
   out_2668724034635220264[275] = 0.0;
   out_2668724034635220264[276] = 0.0;
   out_2668724034635220264[277] = 0.0;
   out_2668724034635220264[278] = 0.0;
   out_2668724034635220264[279] = 0.0;
   out_2668724034635220264[280] = 0.0;
   out_2668724034635220264[281] = 0.0;
   out_2668724034635220264[282] = 0.0;
   out_2668724034635220264[283] = 0.0;
   out_2668724034635220264[284] = 0.0;
   out_2668724034635220264[285] = 1.0;
   out_2668724034635220264[286] = 0.0;
   out_2668724034635220264[287] = 0.0;
   out_2668724034635220264[288] = 0.0;
   out_2668724034635220264[289] = 0.0;
   out_2668724034635220264[290] = 0.0;
   out_2668724034635220264[291] = 0.0;
   out_2668724034635220264[292] = 0.0;
   out_2668724034635220264[293] = 0.0;
   out_2668724034635220264[294] = 0.0;
   out_2668724034635220264[295] = 0.0;
   out_2668724034635220264[296] = 0.0;
   out_2668724034635220264[297] = 0.0;
   out_2668724034635220264[298] = 0.0;
   out_2668724034635220264[299] = 0.0;
   out_2668724034635220264[300] = 0.0;
   out_2668724034635220264[301] = 0.0;
   out_2668724034635220264[302] = 0.0;
   out_2668724034635220264[303] = 0.0;
   out_2668724034635220264[304] = 1.0;
   out_2668724034635220264[305] = 0.0;
   out_2668724034635220264[306] = 0.0;
   out_2668724034635220264[307] = 0.0;
   out_2668724034635220264[308] = 0.0;
   out_2668724034635220264[309] = 0.0;
   out_2668724034635220264[310] = 0.0;
   out_2668724034635220264[311] = 0.0;
   out_2668724034635220264[312] = 0.0;
   out_2668724034635220264[313] = 0.0;
   out_2668724034635220264[314] = 0.0;
   out_2668724034635220264[315] = 0.0;
   out_2668724034635220264[316] = 0.0;
   out_2668724034635220264[317] = 0.0;
   out_2668724034635220264[318] = 0.0;
   out_2668724034635220264[319] = 0.0;
   out_2668724034635220264[320] = 0.0;
   out_2668724034635220264[321] = 0.0;
   out_2668724034635220264[322] = 0.0;
   out_2668724034635220264[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_9201625055442330332) {
   out_9201625055442330332[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_9201625055442330332[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_9201625055442330332[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_9201625055442330332[3] = dt*state[12] + state[3];
   out_9201625055442330332[4] = dt*state[13] + state[4];
   out_9201625055442330332[5] = dt*state[14] + state[5];
   out_9201625055442330332[6] = state[6];
   out_9201625055442330332[7] = state[7];
   out_9201625055442330332[8] = state[8];
   out_9201625055442330332[9] = state[9];
   out_9201625055442330332[10] = state[10];
   out_9201625055442330332[11] = state[11];
   out_9201625055442330332[12] = state[12];
   out_9201625055442330332[13] = state[13];
   out_9201625055442330332[14] = state[14];
   out_9201625055442330332[15] = state[15];
   out_9201625055442330332[16] = state[16];
   out_9201625055442330332[17] = state[17];
}
void F_fun(double *state, double dt, double *out_435223935958301203) {
   out_435223935958301203[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435223935958301203[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435223935958301203[2] = 0;
   out_435223935958301203[3] = 0;
   out_435223935958301203[4] = 0;
   out_435223935958301203[5] = 0;
   out_435223935958301203[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435223935958301203[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435223935958301203[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_435223935958301203[9] = 0;
   out_435223935958301203[10] = 0;
   out_435223935958301203[11] = 0;
   out_435223935958301203[12] = 0;
   out_435223935958301203[13] = 0;
   out_435223935958301203[14] = 0;
   out_435223935958301203[15] = 0;
   out_435223935958301203[16] = 0;
   out_435223935958301203[17] = 0;
   out_435223935958301203[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435223935958301203[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435223935958301203[20] = 0;
   out_435223935958301203[21] = 0;
   out_435223935958301203[22] = 0;
   out_435223935958301203[23] = 0;
   out_435223935958301203[24] = 0;
   out_435223935958301203[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435223935958301203[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_435223935958301203[27] = 0;
   out_435223935958301203[28] = 0;
   out_435223935958301203[29] = 0;
   out_435223935958301203[30] = 0;
   out_435223935958301203[31] = 0;
   out_435223935958301203[32] = 0;
   out_435223935958301203[33] = 0;
   out_435223935958301203[34] = 0;
   out_435223935958301203[35] = 0;
   out_435223935958301203[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435223935958301203[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435223935958301203[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435223935958301203[39] = 0;
   out_435223935958301203[40] = 0;
   out_435223935958301203[41] = 0;
   out_435223935958301203[42] = 0;
   out_435223935958301203[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435223935958301203[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_435223935958301203[45] = 0;
   out_435223935958301203[46] = 0;
   out_435223935958301203[47] = 0;
   out_435223935958301203[48] = 0;
   out_435223935958301203[49] = 0;
   out_435223935958301203[50] = 0;
   out_435223935958301203[51] = 0;
   out_435223935958301203[52] = 0;
   out_435223935958301203[53] = 0;
   out_435223935958301203[54] = 0;
   out_435223935958301203[55] = 0;
   out_435223935958301203[56] = 0;
   out_435223935958301203[57] = 1;
   out_435223935958301203[58] = 0;
   out_435223935958301203[59] = 0;
   out_435223935958301203[60] = 0;
   out_435223935958301203[61] = 0;
   out_435223935958301203[62] = 0;
   out_435223935958301203[63] = 0;
   out_435223935958301203[64] = 0;
   out_435223935958301203[65] = 0;
   out_435223935958301203[66] = dt;
   out_435223935958301203[67] = 0;
   out_435223935958301203[68] = 0;
   out_435223935958301203[69] = 0;
   out_435223935958301203[70] = 0;
   out_435223935958301203[71] = 0;
   out_435223935958301203[72] = 0;
   out_435223935958301203[73] = 0;
   out_435223935958301203[74] = 0;
   out_435223935958301203[75] = 0;
   out_435223935958301203[76] = 1;
   out_435223935958301203[77] = 0;
   out_435223935958301203[78] = 0;
   out_435223935958301203[79] = 0;
   out_435223935958301203[80] = 0;
   out_435223935958301203[81] = 0;
   out_435223935958301203[82] = 0;
   out_435223935958301203[83] = 0;
   out_435223935958301203[84] = 0;
   out_435223935958301203[85] = dt;
   out_435223935958301203[86] = 0;
   out_435223935958301203[87] = 0;
   out_435223935958301203[88] = 0;
   out_435223935958301203[89] = 0;
   out_435223935958301203[90] = 0;
   out_435223935958301203[91] = 0;
   out_435223935958301203[92] = 0;
   out_435223935958301203[93] = 0;
   out_435223935958301203[94] = 0;
   out_435223935958301203[95] = 1;
   out_435223935958301203[96] = 0;
   out_435223935958301203[97] = 0;
   out_435223935958301203[98] = 0;
   out_435223935958301203[99] = 0;
   out_435223935958301203[100] = 0;
   out_435223935958301203[101] = 0;
   out_435223935958301203[102] = 0;
   out_435223935958301203[103] = 0;
   out_435223935958301203[104] = dt;
   out_435223935958301203[105] = 0;
   out_435223935958301203[106] = 0;
   out_435223935958301203[107] = 0;
   out_435223935958301203[108] = 0;
   out_435223935958301203[109] = 0;
   out_435223935958301203[110] = 0;
   out_435223935958301203[111] = 0;
   out_435223935958301203[112] = 0;
   out_435223935958301203[113] = 0;
   out_435223935958301203[114] = 1;
   out_435223935958301203[115] = 0;
   out_435223935958301203[116] = 0;
   out_435223935958301203[117] = 0;
   out_435223935958301203[118] = 0;
   out_435223935958301203[119] = 0;
   out_435223935958301203[120] = 0;
   out_435223935958301203[121] = 0;
   out_435223935958301203[122] = 0;
   out_435223935958301203[123] = 0;
   out_435223935958301203[124] = 0;
   out_435223935958301203[125] = 0;
   out_435223935958301203[126] = 0;
   out_435223935958301203[127] = 0;
   out_435223935958301203[128] = 0;
   out_435223935958301203[129] = 0;
   out_435223935958301203[130] = 0;
   out_435223935958301203[131] = 0;
   out_435223935958301203[132] = 0;
   out_435223935958301203[133] = 1;
   out_435223935958301203[134] = 0;
   out_435223935958301203[135] = 0;
   out_435223935958301203[136] = 0;
   out_435223935958301203[137] = 0;
   out_435223935958301203[138] = 0;
   out_435223935958301203[139] = 0;
   out_435223935958301203[140] = 0;
   out_435223935958301203[141] = 0;
   out_435223935958301203[142] = 0;
   out_435223935958301203[143] = 0;
   out_435223935958301203[144] = 0;
   out_435223935958301203[145] = 0;
   out_435223935958301203[146] = 0;
   out_435223935958301203[147] = 0;
   out_435223935958301203[148] = 0;
   out_435223935958301203[149] = 0;
   out_435223935958301203[150] = 0;
   out_435223935958301203[151] = 0;
   out_435223935958301203[152] = 1;
   out_435223935958301203[153] = 0;
   out_435223935958301203[154] = 0;
   out_435223935958301203[155] = 0;
   out_435223935958301203[156] = 0;
   out_435223935958301203[157] = 0;
   out_435223935958301203[158] = 0;
   out_435223935958301203[159] = 0;
   out_435223935958301203[160] = 0;
   out_435223935958301203[161] = 0;
   out_435223935958301203[162] = 0;
   out_435223935958301203[163] = 0;
   out_435223935958301203[164] = 0;
   out_435223935958301203[165] = 0;
   out_435223935958301203[166] = 0;
   out_435223935958301203[167] = 0;
   out_435223935958301203[168] = 0;
   out_435223935958301203[169] = 0;
   out_435223935958301203[170] = 0;
   out_435223935958301203[171] = 1;
   out_435223935958301203[172] = 0;
   out_435223935958301203[173] = 0;
   out_435223935958301203[174] = 0;
   out_435223935958301203[175] = 0;
   out_435223935958301203[176] = 0;
   out_435223935958301203[177] = 0;
   out_435223935958301203[178] = 0;
   out_435223935958301203[179] = 0;
   out_435223935958301203[180] = 0;
   out_435223935958301203[181] = 0;
   out_435223935958301203[182] = 0;
   out_435223935958301203[183] = 0;
   out_435223935958301203[184] = 0;
   out_435223935958301203[185] = 0;
   out_435223935958301203[186] = 0;
   out_435223935958301203[187] = 0;
   out_435223935958301203[188] = 0;
   out_435223935958301203[189] = 0;
   out_435223935958301203[190] = 1;
   out_435223935958301203[191] = 0;
   out_435223935958301203[192] = 0;
   out_435223935958301203[193] = 0;
   out_435223935958301203[194] = 0;
   out_435223935958301203[195] = 0;
   out_435223935958301203[196] = 0;
   out_435223935958301203[197] = 0;
   out_435223935958301203[198] = 0;
   out_435223935958301203[199] = 0;
   out_435223935958301203[200] = 0;
   out_435223935958301203[201] = 0;
   out_435223935958301203[202] = 0;
   out_435223935958301203[203] = 0;
   out_435223935958301203[204] = 0;
   out_435223935958301203[205] = 0;
   out_435223935958301203[206] = 0;
   out_435223935958301203[207] = 0;
   out_435223935958301203[208] = 0;
   out_435223935958301203[209] = 1;
   out_435223935958301203[210] = 0;
   out_435223935958301203[211] = 0;
   out_435223935958301203[212] = 0;
   out_435223935958301203[213] = 0;
   out_435223935958301203[214] = 0;
   out_435223935958301203[215] = 0;
   out_435223935958301203[216] = 0;
   out_435223935958301203[217] = 0;
   out_435223935958301203[218] = 0;
   out_435223935958301203[219] = 0;
   out_435223935958301203[220] = 0;
   out_435223935958301203[221] = 0;
   out_435223935958301203[222] = 0;
   out_435223935958301203[223] = 0;
   out_435223935958301203[224] = 0;
   out_435223935958301203[225] = 0;
   out_435223935958301203[226] = 0;
   out_435223935958301203[227] = 0;
   out_435223935958301203[228] = 1;
   out_435223935958301203[229] = 0;
   out_435223935958301203[230] = 0;
   out_435223935958301203[231] = 0;
   out_435223935958301203[232] = 0;
   out_435223935958301203[233] = 0;
   out_435223935958301203[234] = 0;
   out_435223935958301203[235] = 0;
   out_435223935958301203[236] = 0;
   out_435223935958301203[237] = 0;
   out_435223935958301203[238] = 0;
   out_435223935958301203[239] = 0;
   out_435223935958301203[240] = 0;
   out_435223935958301203[241] = 0;
   out_435223935958301203[242] = 0;
   out_435223935958301203[243] = 0;
   out_435223935958301203[244] = 0;
   out_435223935958301203[245] = 0;
   out_435223935958301203[246] = 0;
   out_435223935958301203[247] = 1;
   out_435223935958301203[248] = 0;
   out_435223935958301203[249] = 0;
   out_435223935958301203[250] = 0;
   out_435223935958301203[251] = 0;
   out_435223935958301203[252] = 0;
   out_435223935958301203[253] = 0;
   out_435223935958301203[254] = 0;
   out_435223935958301203[255] = 0;
   out_435223935958301203[256] = 0;
   out_435223935958301203[257] = 0;
   out_435223935958301203[258] = 0;
   out_435223935958301203[259] = 0;
   out_435223935958301203[260] = 0;
   out_435223935958301203[261] = 0;
   out_435223935958301203[262] = 0;
   out_435223935958301203[263] = 0;
   out_435223935958301203[264] = 0;
   out_435223935958301203[265] = 0;
   out_435223935958301203[266] = 1;
   out_435223935958301203[267] = 0;
   out_435223935958301203[268] = 0;
   out_435223935958301203[269] = 0;
   out_435223935958301203[270] = 0;
   out_435223935958301203[271] = 0;
   out_435223935958301203[272] = 0;
   out_435223935958301203[273] = 0;
   out_435223935958301203[274] = 0;
   out_435223935958301203[275] = 0;
   out_435223935958301203[276] = 0;
   out_435223935958301203[277] = 0;
   out_435223935958301203[278] = 0;
   out_435223935958301203[279] = 0;
   out_435223935958301203[280] = 0;
   out_435223935958301203[281] = 0;
   out_435223935958301203[282] = 0;
   out_435223935958301203[283] = 0;
   out_435223935958301203[284] = 0;
   out_435223935958301203[285] = 1;
   out_435223935958301203[286] = 0;
   out_435223935958301203[287] = 0;
   out_435223935958301203[288] = 0;
   out_435223935958301203[289] = 0;
   out_435223935958301203[290] = 0;
   out_435223935958301203[291] = 0;
   out_435223935958301203[292] = 0;
   out_435223935958301203[293] = 0;
   out_435223935958301203[294] = 0;
   out_435223935958301203[295] = 0;
   out_435223935958301203[296] = 0;
   out_435223935958301203[297] = 0;
   out_435223935958301203[298] = 0;
   out_435223935958301203[299] = 0;
   out_435223935958301203[300] = 0;
   out_435223935958301203[301] = 0;
   out_435223935958301203[302] = 0;
   out_435223935958301203[303] = 0;
   out_435223935958301203[304] = 1;
   out_435223935958301203[305] = 0;
   out_435223935958301203[306] = 0;
   out_435223935958301203[307] = 0;
   out_435223935958301203[308] = 0;
   out_435223935958301203[309] = 0;
   out_435223935958301203[310] = 0;
   out_435223935958301203[311] = 0;
   out_435223935958301203[312] = 0;
   out_435223935958301203[313] = 0;
   out_435223935958301203[314] = 0;
   out_435223935958301203[315] = 0;
   out_435223935958301203[316] = 0;
   out_435223935958301203[317] = 0;
   out_435223935958301203[318] = 0;
   out_435223935958301203[319] = 0;
   out_435223935958301203[320] = 0;
   out_435223935958301203[321] = 0;
   out_435223935958301203[322] = 0;
   out_435223935958301203[323] = 1;
}
void h_4(double *state, double *unused, double *out_6259395131604772748) {
   out_6259395131604772748[0] = state[6] + state[9];
   out_6259395131604772748[1] = state[7] + state[10];
   out_6259395131604772748[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_4488422760541517125) {
   out_4488422760541517125[0] = 0;
   out_4488422760541517125[1] = 0;
   out_4488422760541517125[2] = 0;
   out_4488422760541517125[3] = 0;
   out_4488422760541517125[4] = 0;
   out_4488422760541517125[5] = 0;
   out_4488422760541517125[6] = 1;
   out_4488422760541517125[7] = 0;
   out_4488422760541517125[8] = 0;
   out_4488422760541517125[9] = 1;
   out_4488422760541517125[10] = 0;
   out_4488422760541517125[11] = 0;
   out_4488422760541517125[12] = 0;
   out_4488422760541517125[13] = 0;
   out_4488422760541517125[14] = 0;
   out_4488422760541517125[15] = 0;
   out_4488422760541517125[16] = 0;
   out_4488422760541517125[17] = 0;
   out_4488422760541517125[18] = 0;
   out_4488422760541517125[19] = 0;
   out_4488422760541517125[20] = 0;
   out_4488422760541517125[21] = 0;
   out_4488422760541517125[22] = 0;
   out_4488422760541517125[23] = 0;
   out_4488422760541517125[24] = 0;
   out_4488422760541517125[25] = 1;
   out_4488422760541517125[26] = 0;
   out_4488422760541517125[27] = 0;
   out_4488422760541517125[28] = 1;
   out_4488422760541517125[29] = 0;
   out_4488422760541517125[30] = 0;
   out_4488422760541517125[31] = 0;
   out_4488422760541517125[32] = 0;
   out_4488422760541517125[33] = 0;
   out_4488422760541517125[34] = 0;
   out_4488422760541517125[35] = 0;
   out_4488422760541517125[36] = 0;
   out_4488422760541517125[37] = 0;
   out_4488422760541517125[38] = 0;
   out_4488422760541517125[39] = 0;
   out_4488422760541517125[40] = 0;
   out_4488422760541517125[41] = 0;
   out_4488422760541517125[42] = 0;
   out_4488422760541517125[43] = 0;
   out_4488422760541517125[44] = 1;
   out_4488422760541517125[45] = 0;
   out_4488422760541517125[46] = 0;
   out_4488422760541517125[47] = 1;
   out_4488422760541517125[48] = 0;
   out_4488422760541517125[49] = 0;
   out_4488422760541517125[50] = 0;
   out_4488422760541517125[51] = 0;
   out_4488422760541517125[52] = 0;
   out_4488422760541517125[53] = 0;
}
void h_10(double *state, double *unused, double *out_8979834360034398189) {
   out_8979834360034398189[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_8979834360034398189[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_8979834360034398189[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_5518597412603733548) {
   out_5518597412603733548[0] = 0;
   out_5518597412603733548[1] = 9.8100000000000005*cos(state[1]);
   out_5518597412603733548[2] = 0;
   out_5518597412603733548[3] = 0;
   out_5518597412603733548[4] = -state[8];
   out_5518597412603733548[5] = state[7];
   out_5518597412603733548[6] = 0;
   out_5518597412603733548[7] = state[5];
   out_5518597412603733548[8] = -state[4];
   out_5518597412603733548[9] = 0;
   out_5518597412603733548[10] = 0;
   out_5518597412603733548[11] = 0;
   out_5518597412603733548[12] = 1;
   out_5518597412603733548[13] = 0;
   out_5518597412603733548[14] = 0;
   out_5518597412603733548[15] = 1;
   out_5518597412603733548[16] = 0;
   out_5518597412603733548[17] = 0;
   out_5518597412603733548[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_5518597412603733548[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_5518597412603733548[20] = 0;
   out_5518597412603733548[21] = state[8];
   out_5518597412603733548[22] = 0;
   out_5518597412603733548[23] = -state[6];
   out_5518597412603733548[24] = -state[5];
   out_5518597412603733548[25] = 0;
   out_5518597412603733548[26] = state[3];
   out_5518597412603733548[27] = 0;
   out_5518597412603733548[28] = 0;
   out_5518597412603733548[29] = 0;
   out_5518597412603733548[30] = 0;
   out_5518597412603733548[31] = 1;
   out_5518597412603733548[32] = 0;
   out_5518597412603733548[33] = 0;
   out_5518597412603733548[34] = 1;
   out_5518597412603733548[35] = 0;
   out_5518597412603733548[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_5518597412603733548[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_5518597412603733548[38] = 0;
   out_5518597412603733548[39] = -state[7];
   out_5518597412603733548[40] = state[6];
   out_5518597412603733548[41] = 0;
   out_5518597412603733548[42] = state[4];
   out_5518597412603733548[43] = -state[3];
   out_5518597412603733548[44] = 0;
   out_5518597412603733548[45] = 0;
   out_5518597412603733548[46] = 0;
   out_5518597412603733548[47] = 0;
   out_5518597412603733548[48] = 0;
   out_5518597412603733548[49] = 0;
   out_5518597412603733548[50] = 1;
   out_5518597412603733548[51] = 0;
   out_5518597412603733548[52] = 0;
   out_5518597412603733548[53] = 1;
}
void h_13(double *state, double *unused, double *out_627396395224579253) {
   out_627396395224579253[0] = state[3];
   out_627396395224579253[1] = state[4];
   out_627396395224579253[2] = state[5];
}
void H_13(double *state, double *unused, double *out_1276148935209184324) {
   out_1276148935209184324[0] = 0;
   out_1276148935209184324[1] = 0;
   out_1276148935209184324[2] = 0;
   out_1276148935209184324[3] = 1;
   out_1276148935209184324[4] = 0;
   out_1276148935209184324[5] = 0;
   out_1276148935209184324[6] = 0;
   out_1276148935209184324[7] = 0;
   out_1276148935209184324[8] = 0;
   out_1276148935209184324[9] = 0;
   out_1276148935209184324[10] = 0;
   out_1276148935209184324[11] = 0;
   out_1276148935209184324[12] = 0;
   out_1276148935209184324[13] = 0;
   out_1276148935209184324[14] = 0;
   out_1276148935209184324[15] = 0;
   out_1276148935209184324[16] = 0;
   out_1276148935209184324[17] = 0;
   out_1276148935209184324[18] = 0;
   out_1276148935209184324[19] = 0;
   out_1276148935209184324[20] = 0;
   out_1276148935209184324[21] = 0;
   out_1276148935209184324[22] = 1;
   out_1276148935209184324[23] = 0;
   out_1276148935209184324[24] = 0;
   out_1276148935209184324[25] = 0;
   out_1276148935209184324[26] = 0;
   out_1276148935209184324[27] = 0;
   out_1276148935209184324[28] = 0;
   out_1276148935209184324[29] = 0;
   out_1276148935209184324[30] = 0;
   out_1276148935209184324[31] = 0;
   out_1276148935209184324[32] = 0;
   out_1276148935209184324[33] = 0;
   out_1276148935209184324[34] = 0;
   out_1276148935209184324[35] = 0;
   out_1276148935209184324[36] = 0;
   out_1276148935209184324[37] = 0;
   out_1276148935209184324[38] = 0;
   out_1276148935209184324[39] = 0;
   out_1276148935209184324[40] = 0;
   out_1276148935209184324[41] = 1;
   out_1276148935209184324[42] = 0;
   out_1276148935209184324[43] = 0;
   out_1276148935209184324[44] = 0;
   out_1276148935209184324[45] = 0;
   out_1276148935209184324[46] = 0;
   out_1276148935209184324[47] = 0;
   out_1276148935209184324[48] = 0;
   out_1276148935209184324[49] = 0;
   out_1276148935209184324[50] = 0;
   out_1276148935209184324[51] = 0;
   out_1276148935209184324[52] = 0;
   out_1276148935209184324[53] = 0;
}
void h_14(double *state, double *unused, double *out_7453788352524990403) {
   out_7453788352524990403[0] = state[6];
   out_7453788352524990403[1] = state[7];
   out_7453788352524990403[2] = state[8];
}
void H_14(double *state, double *unused, double *out_7571211192836889421) {
   out_7571211192836889421[0] = 0;
   out_7571211192836889421[1] = 0;
   out_7571211192836889421[2] = 0;
   out_7571211192836889421[3] = 0;
   out_7571211192836889421[4] = 0;
   out_7571211192836889421[5] = 0;
   out_7571211192836889421[6] = 1;
   out_7571211192836889421[7] = 0;
   out_7571211192836889421[8] = 0;
   out_7571211192836889421[9] = 0;
   out_7571211192836889421[10] = 0;
   out_7571211192836889421[11] = 0;
   out_7571211192836889421[12] = 0;
   out_7571211192836889421[13] = 0;
   out_7571211192836889421[14] = 0;
   out_7571211192836889421[15] = 0;
   out_7571211192836889421[16] = 0;
   out_7571211192836889421[17] = 0;
   out_7571211192836889421[18] = 0;
   out_7571211192836889421[19] = 0;
   out_7571211192836889421[20] = 0;
   out_7571211192836889421[21] = 0;
   out_7571211192836889421[22] = 0;
   out_7571211192836889421[23] = 0;
   out_7571211192836889421[24] = 0;
   out_7571211192836889421[25] = 1;
   out_7571211192836889421[26] = 0;
   out_7571211192836889421[27] = 0;
   out_7571211192836889421[28] = 0;
   out_7571211192836889421[29] = 0;
   out_7571211192836889421[30] = 0;
   out_7571211192836889421[31] = 0;
   out_7571211192836889421[32] = 0;
   out_7571211192836889421[33] = 0;
   out_7571211192836889421[34] = 0;
   out_7571211192836889421[35] = 0;
   out_7571211192836889421[36] = 0;
   out_7571211192836889421[37] = 0;
   out_7571211192836889421[38] = 0;
   out_7571211192836889421[39] = 0;
   out_7571211192836889421[40] = 0;
   out_7571211192836889421[41] = 0;
   out_7571211192836889421[42] = 0;
   out_7571211192836889421[43] = 0;
   out_7571211192836889421[44] = 1;
   out_7571211192836889421[45] = 0;
   out_7571211192836889421[46] = 0;
   out_7571211192836889421[47] = 0;
   out_7571211192836889421[48] = 0;
   out_7571211192836889421[49] = 0;
   out_7571211192836889421[50] = 0;
   out_7571211192836889421[51] = 0;
   out_7571211192836889421[52] = 0;
   out_7571211192836889421[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_486750963754107954) {
  err_fun(nom_x, delta_x, out_486750963754107954);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1555487183493314770) {
  inv_err_fun(nom_x, true_x, out_1555487183493314770);
}
void pose_H_mod_fun(double *state, double *out_2668724034635220264) {
  H_mod_fun(state, out_2668724034635220264);
}
void pose_f_fun(double *state, double dt, double *out_9201625055442330332) {
  f_fun(state,  dt, out_9201625055442330332);
}
void pose_F_fun(double *state, double dt, double *out_435223935958301203) {
  F_fun(state,  dt, out_435223935958301203);
}
void pose_h_4(double *state, double *unused, double *out_6259395131604772748) {
  h_4(state, unused, out_6259395131604772748);
}
void pose_H_4(double *state, double *unused, double *out_4488422760541517125) {
  H_4(state, unused, out_4488422760541517125);
}
void pose_h_10(double *state, double *unused, double *out_8979834360034398189) {
  h_10(state, unused, out_8979834360034398189);
}
void pose_H_10(double *state, double *unused, double *out_5518597412603733548) {
  H_10(state, unused, out_5518597412603733548);
}
void pose_h_13(double *state, double *unused, double *out_627396395224579253) {
  h_13(state, unused, out_627396395224579253);
}
void pose_H_13(double *state, double *unused, double *out_1276148935209184324) {
  H_13(state, unused, out_1276148935209184324);
}
void pose_h_14(double *state, double *unused, double *out_7453788352524990403) {
  h_14(state, unused, out_7453788352524990403);
}
void pose_H_14(double *state, double *unused, double *out_7571211192836889421) {
  H_14(state, unused, out_7571211192836889421);
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
