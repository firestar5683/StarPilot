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
void err_fun(double *nom_x, double *delta_x, double *out_4223042806110963609) {
   out_4223042806110963609[0] = delta_x[0] + nom_x[0];
   out_4223042806110963609[1] = delta_x[1] + nom_x[1];
   out_4223042806110963609[2] = delta_x[2] + nom_x[2];
   out_4223042806110963609[3] = delta_x[3] + nom_x[3];
   out_4223042806110963609[4] = delta_x[4] + nom_x[4];
   out_4223042806110963609[5] = delta_x[5] + nom_x[5];
   out_4223042806110963609[6] = delta_x[6] + nom_x[6];
   out_4223042806110963609[7] = delta_x[7] + nom_x[7];
   out_4223042806110963609[8] = delta_x[8] + nom_x[8];
   out_4223042806110963609[9] = delta_x[9] + nom_x[9];
   out_4223042806110963609[10] = delta_x[10] + nom_x[10];
   out_4223042806110963609[11] = delta_x[11] + nom_x[11];
   out_4223042806110963609[12] = delta_x[12] + nom_x[12];
   out_4223042806110963609[13] = delta_x[13] + nom_x[13];
   out_4223042806110963609[14] = delta_x[14] + nom_x[14];
   out_4223042806110963609[15] = delta_x[15] + nom_x[15];
   out_4223042806110963609[16] = delta_x[16] + nom_x[16];
   out_4223042806110963609[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8530086622469742933) {
   out_8530086622469742933[0] = -nom_x[0] + true_x[0];
   out_8530086622469742933[1] = -nom_x[1] + true_x[1];
   out_8530086622469742933[2] = -nom_x[2] + true_x[2];
   out_8530086622469742933[3] = -nom_x[3] + true_x[3];
   out_8530086622469742933[4] = -nom_x[4] + true_x[4];
   out_8530086622469742933[5] = -nom_x[5] + true_x[5];
   out_8530086622469742933[6] = -nom_x[6] + true_x[6];
   out_8530086622469742933[7] = -nom_x[7] + true_x[7];
   out_8530086622469742933[8] = -nom_x[8] + true_x[8];
   out_8530086622469742933[9] = -nom_x[9] + true_x[9];
   out_8530086622469742933[10] = -nom_x[10] + true_x[10];
   out_8530086622469742933[11] = -nom_x[11] + true_x[11];
   out_8530086622469742933[12] = -nom_x[12] + true_x[12];
   out_8530086622469742933[13] = -nom_x[13] + true_x[13];
   out_8530086622469742933[14] = -nom_x[14] + true_x[14];
   out_8530086622469742933[15] = -nom_x[15] + true_x[15];
   out_8530086622469742933[16] = -nom_x[16] + true_x[16];
   out_8530086622469742933[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_8909363854772424894) {
   out_8909363854772424894[0] = 1.0;
   out_8909363854772424894[1] = 0.0;
   out_8909363854772424894[2] = 0.0;
   out_8909363854772424894[3] = 0.0;
   out_8909363854772424894[4] = 0.0;
   out_8909363854772424894[5] = 0.0;
   out_8909363854772424894[6] = 0.0;
   out_8909363854772424894[7] = 0.0;
   out_8909363854772424894[8] = 0.0;
   out_8909363854772424894[9] = 0.0;
   out_8909363854772424894[10] = 0.0;
   out_8909363854772424894[11] = 0.0;
   out_8909363854772424894[12] = 0.0;
   out_8909363854772424894[13] = 0.0;
   out_8909363854772424894[14] = 0.0;
   out_8909363854772424894[15] = 0.0;
   out_8909363854772424894[16] = 0.0;
   out_8909363854772424894[17] = 0.0;
   out_8909363854772424894[18] = 0.0;
   out_8909363854772424894[19] = 1.0;
   out_8909363854772424894[20] = 0.0;
   out_8909363854772424894[21] = 0.0;
   out_8909363854772424894[22] = 0.0;
   out_8909363854772424894[23] = 0.0;
   out_8909363854772424894[24] = 0.0;
   out_8909363854772424894[25] = 0.0;
   out_8909363854772424894[26] = 0.0;
   out_8909363854772424894[27] = 0.0;
   out_8909363854772424894[28] = 0.0;
   out_8909363854772424894[29] = 0.0;
   out_8909363854772424894[30] = 0.0;
   out_8909363854772424894[31] = 0.0;
   out_8909363854772424894[32] = 0.0;
   out_8909363854772424894[33] = 0.0;
   out_8909363854772424894[34] = 0.0;
   out_8909363854772424894[35] = 0.0;
   out_8909363854772424894[36] = 0.0;
   out_8909363854772424894[37] = 0.0;
   out_8909363854772424894[38] = 1.0;
   out_8909363854772424894[39] = 0.0;
   out_8909363854772424894[40] = 0.0;
   out_8909363854772424894[41] = 0.0;
   out_8909363854772424894[42] = 0.0;
   out_8909363854772424894[43] = 0.0;
   out_8909363854772424894[44] = 0.0;
   out_8909363854772424894[45] = 0.0;
   out_8909363854772424894[46] = 0.0;
   out_8909363854772424894[47] = 0.0;
   out_8909363854772424894[48] = 0.0;
   out_8909363854772424894[49] = 0.0;
   out_8909363854772424894[50] = 0.0;
   out_8909363854772424894[51] = 0.0;
   out_8909363854772424894[52] = 0.0;
   out_8909363854772424894[53] = 0.0;
   out_8909363854772424894[54] = 0.0;
   out_8909363854772424894[55] = 0.0;
   out_8909363854772424894[56] = 0.0;
   out_8909363854772424894[57] = 1.0;
   out_8909363854772424894[58] = 0.0;
   out_8909363854772424894[59] = 0.0;
   out_8909363854772424894[60] = 0.0;
   out_8909363854772424894[61] = 0.0;
   out_8909363854772424894[62] = 0.0;
   out_8909363854772424894[63] = 0.0;
   out_8909363854772424894[64] = 0.0;
   out_8909363854772424894[65] = 0.0;
   out_8909363854772424894[66] = 0.0;
   out_8909363854772424894[67] = 0.0;
   out_8909363854772424894[68] = 0.0;
   out_8909363854772424894[69] = 0.0;
   out_8909363854772424894[70] = 0.0;
   out_8909363854772424894[71] = 0.0;
   out_8909363854772424894[72] = 0.0;
   out_8909363854772424894[73] = 0.0;
   out_8909363854772424894[74] = 0.0;
   out_8909363854772424894[75] = 0.0;
   out_8909363854772424894[76] = 1.0;
   out_8909363854772424894[77] = 0.0;
   out_8909363854772424894[78] = 0.0;
   out_8909363854772424894[79] = 0.0;
   out_8909363854772424894[80] = 0.0;
   out_8909363854772424894[81] = 0.0;
   out_8909363854772424894[82] = 0.0;
   out_8909363854772424894[83] = 0.0;
   out_8909363854772424894[84] = 0.0;
   out_8909363854772424894[85] = 0.0;
   out_8909363854772424894[86] = 0.0;
   out_8909363854772424894[87] = 0.0;
   out_8909363854772424894[88] = 0.0;
   out_8909363854772424894[89] = 0.0;
   out_8909363854772424894[90] = 0.0;
   out_8909363854772424894[91] = 0.0;
   out_8909363854772424894[92] = 0.0;
   out_8909363854772424894[93] = 0.0;
   out_8909363854772424894[94] = 0.0;
   out_8909363854772424894[95] = 1.0;
   out_8909363854772424894[96] = 0.0;
   out_8909363854772424894[97] = 0.0;
   out_8909363854772424894[98] = 0.0;
   out_8909363854772424894[99] = 0.0;
   out_8909363854772424894[100] = 0.0;
   out_8909363854772424894[101] = 0.0;
   out_8909363854772424894[102] = 0.0;
   out_8909363854772424894[103] = 0.0;
   out_8909363854772424894[104] = 0.0;
   out_8909363854772424894[105] = 0.0;
   out_8909363854772424894[106] = 0.0;
   out_8909363854772424894[107] = 0.0;
   out_8909363854772424894[108] = 0.0;
   out_8909363854772424894[109] = 0.0;
   out_8909363854772424894[110] = 0.0;
   out_8909363854772424894[111] = 0.0;
   out_8909363854772424894[112] = 0.0;
   out_8909363854772424894[113] = 0.0;
   out_8909363854772424894[114] = 1.0;
   out_8909363854772424894[115] = 0.0;
   out_8909363854772424894[116] = 0.0;
   out_8909363854772424894[117] = 0.0;
   out_8909363854772424894[118] = 0.0;
   out_8909363854772424894[119] = 0.0;
   out_8909363854772424894[120] = 0.0;
   out_8909363854772424894[121] = 0.0;
   out_8909363854772424894[122] = 0.0;
   out_8909363854772424894[123] = 0.0;
   out_8909363854772424894[124] = 0.0;
   out_8909363854772424894[125] = 0.0;
   out_8909363854772424894[126] = 0.0;
   out_8909363854772424894[127] = 0.0;
   out_8909363854772424894[128] = 0.0;
   out_8909363854772424894[129] = 0.0;
   out_8909363854772424894[130] = 0.0;
   out_8909363854772424894[131] = 0.0;
   out_8909363854772424894[132] = 0.0;
   out_8909363854772424894[133] = 1.0;
   out_8909363854772424894[134] = 0.0;
   out_8909363854772424894[135] = 0.0;
   out_8909363854772424894[136] = 0.0;
   out_8909363854772424894[137] = 0.0;
   out_8909363854772424894[138] = 0.0;
   out_8909363854772424894[139] = 0.0;
   out_8909363854772424894[140] = 0.0;
   out_8909363854772424894[141] = 0.0;
   out_8909363854772424894[142] = 0.0;
   out_8909363854772424894[143] = 0.0;
   out_8909363854772424894[144] = 0.0;
   out_8909363854772424894[145] = 0.0;
   out_8909363854772424894[146] = 0.0;
   out_8909363854772424894[147] = 0.0;
   out_8909363854772424894[148] = 0.0;
   out_8909363854772424894[149] = 0.0;
   out_8909363854772424894[150] = 0.0;
   out_8909363854772424894[151] = 0.0;
   out_8909363854772424894[152] = 1.0;
   out_8909363854772424894[153] = 0.0;
   out_8909363854772424894[154] = 0.0;
   out_8909363854772424894[155] = 0.0;
   out_8909363854772424894[156] = 0.0;
   out_8909363854772424894[157] = 0.0;
   out_8909363854772424894[158] = 0.0;
   out_8909363854772424894[159] = 0.0;
   out_8909363854772424894[160] = 0.0;
   out_8909363854772424894[161] = 0.0;
   out_8909363854772424894[162] = 0.0;
   out_8909363854772424894[163] = 0.0;
   out_8909363854772424894[164] = 0.0;
   out_8909363854772424894[165] = 0.0;
   out_8909363854772424894[166] = 0.0;
   out_8909363854772424894[167] = 0.0;
   out_8909363854772424894[168] = 0.0;
   out_8909363854772424894[169] = 0.0;
   out_8909363854772424894[170] = 0.0;
   out_8909363854772424894[171] = 1.0;
   out_8909363854772424894[172] = 0.0;
   out_8909363854772424894[173] = 0.0;
   out_8909363854772424894[174] = 0.0;
   out_8909363854772424894[175] = 0.0;
   out_8909363854772424894[176] = 0.0;
   out_8909363854772424894[177] = 0.0;
   out_8909363854772424894[178] = 0.0;
   out_8909363854772424894[179] = 0.0;
   out_8909363854772424894[180] = 0.0;
   out_8909363854772424894[181] = 0.0;
   out_8909363854772424894[182] = 0.0;
   out_8909363854772424894[183] = 0.0;
   out_8909363854772424894[184] = 0.0;
   out_8909363854772424894[185] = 0.0;
   out_8909363854772424894[186] = 0.0;
   out_8909363854772424894[187] = 0.0;
   out_8909363854772424894[188] = 0.0;
   out_8909363854772424894[189] = 0.0;
   out_8909363854772424894[190] = 1.0;
   out_8909363854772424894[191] = 0.0;
   out_8909363854772424894[192] = 0.0;
   out_8909363854772424894[193] = 0.0;
   out_8909363854772424894[194] = 0.0;
   out_8909363854772424894[195] = 0.0;
   out_8909363854772424894[196] = 0.0;
   out_8909363854772424894[197] = 0.0;
   out_8909363854772424894[198] = 0.0;
   out_8909363854772424894[199] = 0.0;
   out_8909363854772424894[200] = 0.0;
   out_8909363854772424894[201] = 0.0;
   out_8909363854772424894[202] = 0.0;
   out_8909363854772424894[203] = 0.0;
   out_8909363854772424894[204] = 0.0;
   out_8909363854772424894[205] = 0.0;
   out_8909363854772424894[206] = 0.0;
   out_8909363854772424894[207] = 0.0;
   out_8909363854772424894[208] = 0.0;
   out_8909363854772424894[209] = 1.0;
   out_8909363854772424894[210] = 0.0;
   out_8909363854772424894[211] = 0.0;
   out_8909363854772424894[212] = 0.0;
   out_8909363854772424894[213] = 0.0;
   out_8909363854772424894[214] = 0.0;
   out_8909363854772424894[215] = 0.0;
   out_8909363854772424894[216] = 0.0;
   out_8909363854772424894[217] = 0.0;
   out_8909363854772424894[218] = 0.0;
   out_8909363854772424894[219] = 0.0;
   out_8909363854772424894[220] = 0.0;
   out_8909363854772424894[221] = 0.0;
   out_8909363854772424894[222] = 0.0;
   out_8909363854772424894[223] = 0.0;
   out_8909363854772424894[224] = 0.0;
   out_8909363854772424894[225] = 0.0;
   out_8909363854772424894[226] = 0.0;
   out_8909363854772424894[227] = 0.0;
   out_8909363854772424894[228] = 1.0;
   out_8909363854772424894[229] = 0.0;
   out_8909363854772424894[230] = 0.0;
   out_8909363854772424894[231] = 0.0;
   out_8909363854772424894[232] = 0.0;
   out_8909363854772424894[233] = 0.0;
   out_8909363854772424894[234] = 0.0;
   out_8909363854772424894[235] = 0.0;
   out_8909363854772424894[236] = 0.0;
   out_8909363854772424894[237] = 0.0;
   out_8909363854772424894[238] = 0.0;
   out_8909363854772424894[239] = 0.0;
   out_8909363854772424894[240] = 0.0;
   out_8909363854772424894[241] = 0.0;
   out_8909363854772424894[242] = 0.0;
   out_8909363854772424894[243] = 0.0;
   out_8909363854772424894[244] = 0.0;
   out_8909363854772424894[245] = 0.0;
   out_8909363854772424894[246] = 0.0;
   out_8909363854772424894[247] = 1.0;
   out_8909363854772424894[248] = 0.0;
   out_8909363854772424894[249] = 0.0;
   out_8909363854772424894[250] = 0.0;
   out_8909363854772424894[251] = 0.0;
   out_8909363854772424894[252] = 0.0;
   out_8909363854772424894[253] = 0.0;
   out_8909363854772424894[254] = 0.0;
   out_8909363854772424894[255] = 0.0;
   out_8909363854772424894[256] = 0.0;
   out_8909363854772424894[257] = 0.0;
   out_8909363854772424894[258] = 0.0;
   out_8909363854772424894[259] = 0.0;
   out_8909363854772424894[260] = 0.0;
   out_8909363854772424894[261] = 0.0;
   out_8909363854772424894[262] = 0.0;
   out_8909363854772424894[263] = 0.0;
   out_8909363854772424894[264] = 0.0;
   out_8909363854772424894[265] = 0.0;
   out_8909363854772424894[266] = 1.0;
   out_8909363854772424894[267] = 0.0;
   out_8909363854772424894[268] = 0.0;
   out_8909363854772424894[269] = 0.0;
   out_8909363854772424894[270] = 0.0;
   out_8909363854772424894[271] = 0.0;
   out_8909363854772424894[272] = 0.0;
   out_8909363854772424894[273] = 0.0;
   out_8909363854772424894[274] = 0.0;
   out_8909363854772424894[275] = 0.0;
   out_8909363854772424894[276] = 0.0;
   out_8909363854772424894[277] = 0.0;
   out_8909363854772424894[278] = 0.0;
   out_8909363854772424894[279] = 0.0;
   out_8909363854772424894[280] = 0.0;
   out_8909363854772424894[281] = 0.0;
   out_8909363854772424894[282] = 0.0;
   out_8909363854772424894[283] = 0.0;
   out_8909363854772424894[284] = 0.0;
   out_8909363854772424894[285] = 1.0;
   out_8909363854772424894[286] = 0.0;
   out_8909363854772424894[287] = 0.0;
   out_8909363854772424894[288] = 0.0;
   out_8909363854772424894[289] = 0.0;
   out_8909363854772424894[290] = 0.0;
   out_8909363854772424894[291] = 0.0;
   out_8909363854772424894[292] = 0.0;
   out_8909363854772424894[293] = 0.0;
   out_8909363854772424894[294] = 0.0;
   out_8909363854772424894[295] = 0.0;
   out_8909363854772424894[296] = 0.0;
   out_8909363854772424894[297] = 0.0;
   out_8909363854772424894[298] = 0.0;
   out_8909363854772424894[299] = 0.0;
   out_8909363854772424894[300] = 0.0;
   out_8909363854772424894[301] = 0.0;
   out_8909363854772424894[302] = 0.0;
   out_8909363854772424894[303] = 0.0;
   out_8909363854772424894[304] = 1.0;
   out_8909363854772424894[305] = 0.0;
   out_8909363854772424894[306] = 0.0;
   out_8909363854772424894[307] = 0.0;
   out_8909363854772424894[308] = 0.0;
   out_8909363854772424894[309] = 0.0;
   out_8909363854772424894[310] = 0.0;
   out_8909363854772424894[311] = 0.0;
   out_8909363854772424894[312] = 0.0;
   out_8909363854772424894[313] = 0.0;
   out_8909363854772424894[314] = 0.0;
   out_8909363854772424894[315] = 0.0;
   out_8909363854772424894[316] = 0.0;
   out_8909363854772424894[317] = 0.0;
   out_8909363854772424894[318] = 0.0;
   out_8909363854772424894[319] = 0.0;
   out_8909363854772424894[320] = 0.0;
   out_8909363854772424894[321] = 0.0;
   out_8909363854772424894[322] = 0.0;
   out_8909363854772424894[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_1291447636833644141) {
   out_1291447636833644141[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_1291447636833644141[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_1291447636833644141[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_1291447636833644141[3] = dt*state[12] + state[3];
   out_1291447636833644141[4] = dt*state[13] + state[4];
   out_1291447636833644141[5] = dt*state[14] + state[5];
   out_1291447636833644141[6] = state[6];
   out_1291447636833644141[7] = state[7];
   out_1291447636833644141[8] = state[8];
   out_1291447636833644141[9] = state[9];
   out_1291447636833644141[10] = state[10];
   out_1291447636833644141[11] = state[11];
   out_1291447636833644141[12] = state[12];
   out_1291447636833644141[13] = state[13];
   out_1291447636833644141[14] = state[14];
   out_1291447636833644141[15] = state[15];
   out_1291447636833644141[16] = state[16];
   out_1291447636833644141[17] = state[17];
}
void F_fun(double *state, double dt, double *out_2156602018501124106) {
   out_2156602018501124106[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2156602018501124106[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2156602018501124106[2] = 0;
   out_2156602018501124106[3] = 0;
   out_2156602018501124106[4] = 0;
   out_2156602018501124106[5] = 0;
   out_2156602018501124106[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2156602018501124106[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2156602018501124106[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_2156602018501124106[9] = 0;
   out_2156602018501124106[10] = 0;
   out_2156602018501124106[11] = 0;
   out_2156602018501124106[12] = 0;
   out_2156602018501124106[13] = 0;
   out_2156602018501124106[14] = 0;
   out_2156602018501124106[15] = 0;
   out_2156602018501124106[16] = 0;
   out_2156602018501124106[17] = 0;
   out_2156602018501124106[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2156602018501124106[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2156602018501124106[20] = 0;
   out_2156602018501124106[21] = 0;
   out_2156602018501124106[22] = 0;
   out_2156602018501124106[23] = 0;
   out_2156602018501124106[24] = 0;
   out_2156602018501124106[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2156602018501124106[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_2156602018501124106[27] = 0;
   out_2156602018501124106[28] = 0;
   out_2156602018501124106[29] = 0;
   out_2156602018501124106[30] = 0;
   out_2156602018501124106[31] = 0;
   out_2156602018501124106[32] = 0;
   out_2156602018501124106[33] = 0;
   out_2156602018501124106[34] = 0;
   out_2156602018501124106[35] = 0;
   out_2156602018501124106[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2156602018501124106[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2156602018501124106[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2156602018501124106[39] = 0;
   out_2156602018501124106[40] = 0;
   out_2156602018501124106[41] = 0;
   out_2156602018501124106[42] = 0;
   out_2156602018501124106[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2156602018501124106[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_2156602018501124106[45] = 0;
   out_2156602018501124106[46] = 0;
   out_2156602018501124106[47] = 0;
   out_2156602018501124106[48] = 0;
   out_2156602018501124106[49] = 0;
   out_2156602018501124106[50] = 0;
   out_2156602018501124106[51] = 0;
   out_2156602018501124106[52] = 0;
   out_2156602018501124106[53] = 0;
   out_2156602018501124106[54] = 0;
   out_2156602018501124106[55] = 0;
   out_2156602018501124106[56] = 0;
   out_2156602018501124106[57] = 1;
   out_2156602018501124106[58] = 0;
   out_2156602018501124106[59] = 0;
   out_2156602018501124106[60] = 0;
   out_2156602018501124106[61] = 0;
   out_2156602018501124106[62] = 0;
   out_2156602018501124106[63] = 0;
   out_2156602018501124106[64] = 0;
   out_2156602018501124106[65] = 0;
   out_2156602018501124106[66] = dt;
   out_2156602018501124106[67] = 0;
   out_2156602018501124106[68] = 0;
   out_2156602018501124106[69] = 0;
   out_2156602018501124106[70] = 0;
   out_2156602018501124106[71] = 0;
   out_2156602018501124106[72] = 0;
   out_2156602018501124106[73] = 0;
   out_2156602018501124106[74] = 0;
   out_2156602018501124106[75] = 0;
   out_2156602018501124106[76] = 1;
   out_2156602018501124106[77] = 0;
   out_2156602018501124106[78] = 0;
   out_2156602018501124106[79] = 0;
   out_2156602018501124106[80] = 0;
   out_2156602018501124106[81] = 0;
   out_2156602018501124106[82] = 0;
   out_2156602018501124106[83] = 0;
   out_2156602018501124106[84] = 0;
   out_2156602018501124106[85] = dt;
   out_2156602018501124106[86] = 0;
   out_2156602018501124106[87] = 0;
   out_2156602018501124106[88] = 0;
   out_2156602018501124106[89] = 0;
   out_2156602018501124106[90] = 0;
   out_2156602018501124106[91] = 0;
   out_2156602018501124106[92] = 0;
   out_2156602018501124106[93] = 0;
   out_2156602018501124106[94] = 0;
   out_2156602018501124106[95] = 1;
   out_2156602018501124106[96] = 0;
   out_2156602018501124106[97] = 0;
   out_2156602018501124106[98] = 0;
   out_2156602018501124106[99] = 0;
   out_2156602018501124106[100] = 0;
   out_2156602018501124106[101] = 0;
   out_2156602018501124106[102] = 0;
   out_2156602018501124106[103] = 0;
   out_2156602018501124106[104] = dt;
   out_2156602018501124106[105] = 0;
   out_2156602018501124106[106] = 0;
   out_2156602018501124106[107] = 0;
   out_2156602018501124106[108] = 0;
   out_2156602018501124106[109] = 0;
   out_2156602018501124106[110] = 0;
   out_2156602018501124106[111] = 0;
   out_2156602018501124106[112] = 0;
   out_2156602018501124106[113] = 0;
   out_2156602018501124106[114] = 1;
   out_2156602018501124106[115] = 0;
   out_2156602018501124106[116] = 0;
   out_2156602018501124106[117] = 0;
   out_2156602018501124106[118] = 0;
   out_2156602018501124106[119] = 0;
   out_2156602018501124106[120] = 0;
   out_2156602018501124106[121] = 0;
   out_2156602018501124106[122] = 0;
   out_2156602018501124106[123] = 0;
   out_2156602018501124106[124] = 0;
   out_2156602018501124106[125] = 0;
   out_2156602018501124106[126] = 0;
   out_2156602018501124106[127] = 0;
   out_2156602018501124106[128] = 0;
   out_2156602018501124106[129] = 0;
   out_2156602018501124106[130] = 0;
   out_2156602018501124106[131] = 0;
   out_2156602018501124106[132] = 0;
   out_2156602018501124106[133] = 1;
   out_2156602018501124106[134] = 0;
   out_2156602018501124106[135] = 0;
   out_2156602018501124106[136] = 0;
   out_2156602018501124106[137] = 0;
   out_2156602018501124106[138] = 0;
   out_2156602018501124106[139] = 0;
   out_2156602018501124106[140] = 0;
   out_2156602018501124106[141] = 0;
   out_2156602018501124106[142] = 0;
   out_2156602018501124106[143] = 0;
   out_2156602018501124106[144] = 0;
   out_2156602018501124106[145] = 0;
   out_2156602018501124106[146] = 0;
   out_2156602018501124106[147] = 0;
   out_2156602018501124106[148] = 0;
   out_2156602018501124106[149] = 0;
   out_2156602018501124106[150] = 0;
   out_2156602018501124106[151] = 0;
   out_2156602018501124106[152] = 1;
   out_2156602018501124106[153] = 0;
   out_2156602018501124106[154] = 0;
   out_2156602018501124106[155] = 0;
   out_2156602018501124106[156] = 0;
   out_2156602018501124106[157] = 0;
   out_2156602018501124106[158] = 0;
   out_2156602018501124106[159] = 0;
   out_2156602018501124106[160] = 0;
   out_2156602018501124106[161] = 0;
   out_2156602018501124106[162] = 0;
   out_2156602018501124106[163] = 0;
   out_2156602018501124106[164] = 0;
   out_2156602018501124106[165] = 0;
   out_2156602018501124106[166] = 0;
   out_2156602018501124106[167] = 0;
   out_2156602018501124106[168] = 0;
   out_2156602018501124106[169] = 0;
   out_2156602018501124106[170] = 0;
   out_2156602018501124106[171] = 1;
   out_2156602018501124106[172] = 0;
   out_2156602018501124106[173] = 0;
   out_2156602018501124106[174] = 0;
   out_2156602018501124106[175] = 0;
   out_2156602018501124106[176] = 0;
   out_2156602018501124106[177] = 0;
   out_2156602018501124106[178] = 0;
   out_2156602018501124106[179] = 0;
   out_2156602018501124106[180] = 0;
   out_2156602018501124106[181] = 0;
   out_2156602018501124106[182] = 0;
   out_2156602018501124106[183] = 0;
   out_2156602018501124106[184] = 0;
   out_2156602018501124106[185] = 0;
   out_2156602018501124106[186] = 0;
   out_2156602018501124106[187] = 0;
   out_2156602018501124106[188] = 0;
   out_2156602018501124106[189] = 0;
   out_2156602018501124106[190] = 1;
   out_2156602018501124106[191] = 0;
   out_2156602018501124106[192] = 0;
   out_2156602018501124106[193] = 0;
   out_2156602018501124106[194] = 0;
   out_2156602018501124106[195] = 0;
   out_2156602018501124106[196] = 0;
   out_2156602018501124106[197] = 0;
   out_2156602018501124106[198] = 0;
   out_2156602018501124106[199] = 0;
   out_2156602018501124106[200] = 0;
   out_2156602018501124106[201] = 0;
   out_2156602018501124106[202] = 0;
   out_2156602018501124106[203] = 0;
   out_2156602018501124106[204] = 0;
   out_2156602018501124106[205] = 0;
   out_2156602018501124106[206] = 0;
   out_2156602018501124106[207] = 0;
   out_2156602018501124106[208] = 0;
   out_2156602018501124106[209] = 1;
   out_2156602018501124106[210] = 0;
   out_2156602018501124106[211] = 0;
   out_2156602018501124106[212] = 0;
   out_2156602018501124106[213] = 0;
   out_2156602018501124106[214] = 0;
   out_2156602018501124106[215] = 0;
   out_2156602018501124106[216] = 0;
   out_2156602018501124106[217] = 0;
   out_2156602018501124106[218] = 0;
   out_2156602018501124106[219] = 0;
   out_2156602018501124106[220] = 0;
   out_2156602018501124106[221] = 0;
   out_2156602018501124106[222] = 0;
   out_2156602018501124106[223] = 0;
   out_2156602018501124106[224] = 0;
   out_2156602018501124106[225] = 0;
   out_2156602018501124106[226] = 0;
   out_2156602018501124106[227] = 0;
   out_2156602018501124106[228] = 1;
   out_2156602018501124106[229] = 0;
   out_2156602018501124106[230] = 0;
   out_2156602018501124106[231] = 0;
   out_2156602018501124106[232] = 0;
   out_2156602018501124106[233] = 0;
   out_2156602018501124106[234] = 0;
   out_2156602018501124106[235] = 0;
   out_2156602018501124106[236] = 0;
   out_2156602018501124106[237] = 0;
   out_2156602018501124106[238] = 0;
   out_2156602018501124106[239] = 0;
   out_2156602018501124106[240] = 0;
   out_2156602018501124106[241] = 0;
   out_2156602018501124106[242] = 0;
   out_2156602018501124106[243] = 0;
   out_2156602018501124106[244] = 0;
   out_2156602018501124106[245] = 0;
   out_2156602018501124106[246] = 0;
   out_2156602018501124106[247] = 1;
   out_2156602018501124106[248] = 0;
   out_2156602018501124106[249] = 0;
   out_2156602018501124106[250] = 0;
   out_2156602018501124106[251] = 0;
   out_2156602018501124106[252] = 0;
   out_2156602018501124106[253] = 0;
   out_2156602018501124106[254] = 0;
   out_2156602018501124106[255] = 0;
   out_2156602018501124106[256] = 0;
   out_2156602018501124106[257] = 0;
   out_2156602018501124106[258] = 0;
   out_2156602018501124106[259] = 0;
   out_2156602018501124106[260] = 0;
   out_2156602018501124106[261] = 0;
   out_2156602018501124106[262] = 0;
   out_2156602018501124106[263] = 0;
   out_2156602018501124106[264] = 0;
   out_2156602018501124106[265] = 0;
   out_2156602018501124106[266] = 1;
   out_2156602018501124106[267] = 0;
   out_2156602018501124106[268] = 0;
   out_2156602018501124106[269] = 0;
   out_2156602018501124106[270] = 0;
   out_2156602018501124106[271] = 0;
   out_2156602018501124106[272] = 0;
   out_2156602018501124106[273] = 0;
   out_2156602018501124106[274] = 0;
   out_2156602018501124106[275] = 0;
   out_2156602018501124106[276] = 0;
   out_2156602018501124106[277] = 0;
   out_2156602018501124106[278] = 0;
   out_2156602018501124106[279] = 0;
   out_2156602018501124106[280] = 0;
   out_2156602018501124106[281] = 0;
   out_2156602018501124106[282] = 0;
   out_2156602018501124106[283] = 0;
   out_2156602018501124106[284] = 0;
   out_2156602018501124106[285] = 1;
   out_2156602018501124106[286] = 0;
   out_2156602018501124106[287] = 0;
   out_2156602018501124106[288] = 0;
   out_2156602018501124106[289] = 0;
   out_2156602018501124106[290] = 0;
   out_2156602018501124106[291] = 0;
   out_2156602018501124106[292] = 0;
   out_2156602018501124106[293] = 0;
   out_2156602018501124106[294] = 0;
   out_2156602018501124106[295] = 0;
   out_2156602018501124106[296] = 0;
   out_2156602018501124106[297] = 0;
   out_2156602018501124106[298] = 0;
   out_2156602018501124106[299] = 0;
   out_2156602018501124106[300] = 0;
   out_2156602018501124106[301] = 0;
   out_2156602018501124106[302] = 0;
   out_2156602018501124106[303] = 0;
   out_2156602018501124106[304] = 1;
   out_2156602018501124106[305] = 0;
   out_2156602018501124106[306] = 0;
   out_2156602018501124106[307] = 0;
   out_2156602018501124106[308] = 0;
   out_2156602018501124106[309] = 0;
   out_2156602018501124106[310] = 0;
   out_2156602018501124106[311] = 0;
   out_2156602018501124106[312] = 0;
   out_2156602018501124106[313] = 0;
   out_2156602018501124106[314] = 0;
   out_2156602018501124106[315] = 0;
   out_2156602018501124106[316] = 0;
   out_2156602018501124106[317] = 0;
   out_2156602018501124106[318] = 0;
   out_2156602018501124106[319] = 0;
   out_2156602018501124106[320] = 0;
   out_2156602018501124106[321] = 0;
   out_2156602018501124106[322] = 0;
   out_2156602018501124106[323] = 1;
}
void h_4(double *state, double *unused, double *out_6395852196578726056) {
   out_6395852196578726056[0] = state[6] + state[9];
   out_6395852196578726056[1] = state[7] + state[10];
   out_6395852196578726056[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_5765573009093219150) {
   out_5765573009093219150[0] = 0;
   out_5765573009093219150[1] = 0;
   out_5765573009093219150[2] = 0;
   out_5765573009093219150[3] = 0;
   out_5765573009093219150[4] = 0;
   out_5765573009093219150[5] = 0;
   out_5765573009093219150[6] = 1;
   out_5765573009093219150[7] = 0;
   out_5765573009093219150[8] = 0;
   out_5765573009093219150[9] = 1;
   out_5765573009093219150[10] = 0;
   out_5765573009093219150[11] = 0;
   out_5765573009093219150[12] = 0;
   out_5765573009093219150[13] = 0;
   out_5765573009093219150[14] = 0;
   out_5765573009093219150[15] = 0;
   out_5765573009093219150[16] = 0;
   out_5765573009093219150[17] = 0;
   out_5765573009093219150[18] = 0;
   out_5765573009093219150[19] = 0;
   out_5765573009093219150[20] = 0;
   out_5765573009093219150[21] = 0;
   out_5765573009093219150[22] = 0;
   out_5765573009093219150[23] = 0;
   out_5765573009093219150[24] = 0;
   out_5765573009093219150[25] = 1;
   out_5765573009093219150[26] = 0;
   out_5765573009093219150[27] = 0;
   out_5765573009093219150[28] = 1;
   out_5765573009093219150[29] = 0;
   out_5765573009093219150[30] = 0;
   out_5765573009093219150[31] = 0;
   out_5765573009093219150[32] = 0;
   out_5765573009093219150[33] = 0;
   out_5765573009093219150[34] = 0;
   out_5765573009093219150[35] = 0;
   out_5765573009093219150[36] = 0;
   out_5765573009093219150[37] = 0;
   out_5765573009093219150[38] = 0;
   out_5765573009093219150[39] = 0;
   out_5765573009093219150[40] = 0;
   out_5765573009093219150[41] = 0;
   out_5765573009093219150[42] = 0;
   out_5765573009093219150[43] = 0;
   out_5765573009093219150[44] = 1;
   out_5765573009093219150[45] = 0;
   out_5765573009093219150[46] = 0;
   out_5765573009093219150[47] = 1;
   out_5765573009093219150[48] = 0;
   out_5765573009093219150[49] = 0;
   out_5765573009093219150[50] = 0;
   out_5765573009093219150[51] = 0;
   out_5765573009093219150[52] = 0;
   out_5765573009093219150[53] = 0;
}
void h_10(double *state, double *unused, double *out_7562508967147311156) {
   out_7562508967147311156[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7562508967147311156[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7562508967147311156[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_4704156203817477126) {
   out_4704156203817477126[0] = 0;
   out_4704156203817477126[1] = 9.8100000000000005*cos(state[1]);
   out_4704156203817477126[2] = 0;
   out_4704156203817477126[3] = 0;
   out_4704156203817477126[4] = -state[8];
   out_4704156203817477126[5] = state[7];
   out_4704156203817477126[6] = 0;
   out_4704156203817477126[7] = state[5];
   out_4704156203817477126[8] = -state[4];
   out_4704156203817477126[9] = 0;
   out_4704156203817477126[10] = 0;
   out_4704156203817477126[11] = 0;
   out_4704156203817477126[12] = 1;
   out_4704156203817477126[13] = 0;
   out_4704156203817477126[14] = 0;
   out_4704156203817477126[15] = 1;
   out_4704156203817477126[16] = 0;
   out_4704156203817477126[17] = 0;
   out_4704156203817477126[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_4704156203817477126[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_4704156203817477126[20] = 0;
   out_4704156203817477126[21] = state[8];
   out_4704156203817477126[22] = 0;
   out_4704156203817477126[23] = -state[6];
   out_4704156203817477126[24] = -state[5];
   out_4704156203817477126[25] = 0;
   out_4704156203817477126[26] = state[3];
   out_4704156203817477126[27] = 0;
   out_4704156203817477126[28] = 0;
   out_4704156203817477126[29] = 0;
   out_4704156203817477126[30] = 0;
   out_4704156203817477126[31] = 1;
   out_4704156203817477126[32] = 0;
   out_4704156203817477126[33] = 0;
   out_4704156203817477126[34] = 1;
   out_4704156203817477126[35] = 0;
   out_4704156203817477126[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_4704156203817477126[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_4704156203817477126[38] = 0;
   out_4704156203817477126[39] = -state[7];
   out_4704156203817477126[40] = state[6];
   out_4704156203817477126[41] = 0;
   out_4704156203817477126[42] = state[4];
   out_4704156203817477126[43] = -state[3];
   out_4704156203817477126[44] = 0;
   out_4704156203817477126[45] = 0;
   out_4704156203817477126[46] = 0;
   out_4704156203817477126[47] = 0;
   out_4704156203817477126[48] = 0;
   out_4704156203817477126[49] = 0;
   out_4704156203817477126[50] = 1;
   out_4704156203817477126[51] = 0;
   out_4704156203817477126[52] = 0;
   out_4704156203817477126[53] = 1;
}
void h_13(double *state, double *unused, double *out_4947379913658815439) {
   out_4947379913658815439[0] = state[3];
   out_4947379913658815439[1] = state[4];
   out_4947379913658815439[2] = state[5];
}
void H_13(double *state, double *unused, double *out_2553299183760886349) {
   out_2553299183760886349[0] = 0;
   out_2553299183760886349[1] = 0;
   out_2553299183760886349[2] = 0;
   out_2553299183760886349[3] = 1;
   out_2553299183760886349[4] = 0;
   out_2553299183760886349[5] = 0;
   out_2553299183760886349[6] = 0;
   out_2553299183760886349[7] = 0;
   out_2553299183760886349[8] = 0;
   out_2553299183760886349[9] = 0;
   out_2553299183760886349[10] = 0;
   out_2553299183760886349[11] = 0;
   out_2553299183760886349[12] = 0;
   out_2553299183760886349[13] = 0;
   out_2553299183760886349[14] = 0;
   out_2553299183760886349[15] = 0;
   out_2553299183760886349[16] = 0;
   out_2553299183760886349[17] = 0;
   out_2553299183760886349[18] = 0;
   out_2553299183760886349[19] = 0;
   out_2553299183760886349[20] = 0;
   out_2553299183760886349[21] = 0;
   out_2553299183760886349[22] = 1;
   out_2553299183760886349[23] = 0;
   out_2553299183760886349[24] = 0;
   out_2553299183760886349[25] = 0;
   out_2553299183760886349[26] = 0;
   out_2553299183760886349[27] = 0;
   out_2553299183760886349[28] = 0;
   out_2553299183760886349[29] = 0;
   out_2553299183760886349[30] = 0;
   out_2553299183760886349[31] = 0;
   out_2553299183760886349[32] = 0;
   out_2553299183760886349[33] = 0;
   out_2553299183760886349[34] = 0;
   out_2553299183760886349[35] = 0;
   out_2553299183760886349[36] = 0;
   out_2553299183760886349[37] = 0;
   out_2553299183760886349[38] = 0;
   out_2553299183760886349[39] = 0;
   out_2553299183760886349[40] = 0;
   out_2553299183760886349[41] = 1;
   out_2553299183760886349[42] = 0;
   out_2553299183760886349[43] = 0;
   out_2553299183760886349[44] = 0;
   out_2553299183760886349[45] = 0;
   out_2553299183760886349[46] = 0;
   out_2553299183760886349[47] = 0;
   out_2553299183760886349[48] = 0;
   out_2553299183760886349[49] = 0;
   out_2553299183760886349[50] = 0;
   out_2553299183760886349[51] = 0;
   out_2553299183760886349[52] = 0;
   out_2553299183760886349[53] = 0;
}
void h_14(double *state, double *unused, double *out_4640800764138358777) {
   out_4640800764138358777[0] = state[6];
   out_4640800764138358777[1] = state[7];
   out_4640800764138358777[2] = state[8];
}
void H_14(double *state, double *unused, double *out_1802332152753734621) {
   out_1802332152753734621[0] = 0;
   out_1802332152753734621[1] = 0;
   out_1802332152753734621[2] = 0;
   out_1802332152753734621[3] = 0;
   out_1802332152753734621[4] = 0;
   out_1802332152753734621[5] = 0;
   out_1802332152753734621[6] = 1;
   out_1802332152753734621[7] = 0;
   out_1802332152753734621[8] = 0;
   out_1802332152753734621[9] = 0;
   out_1802332152753734621[10] = 0;
   out_1802332152753734621[11] = 0;
   out_1802332152753734621[12] = 0;
   out_1802332152753734621[13] = 0;
   out_1802332152753734621[14] = 0;
   out_1802332152753734621[15] = 0;
   out_1802332152753734621[16] = 0;
   out_1802332152753734621[17] = 0;
   out_1802332152753734621[18] = 0;
   out_1802332152753734621[19] = 0;
   out_1802332152753734621[20] = 0;
   out_1802332152753734621[21] = 0;
   out_1802332152753734621[22] = 0;
   out_1802332152753734621[23] = 0;
   out_1802332152753734621[24] = 0;
   out_1802332152753734621[25] = 1;
   out_1802332152753734621[26] = 0;
   out_1802332152753734621[27] = 0;
   out_1802332152753734621[28] = 0;
   out_1802332152753734621[29] = 0;
   out_1802332152753734621[30] = 0;
   out_1802332152753734621[31] = 0;
   out_1802332152753734621[32] = 0;
   out_1802332152753734621[33] = 0;
   out_1802332152753734621[34] = 0;
   out_1802332152753734621[35] = 0;
   out_1802332152753734621[36] = 0;
   out_1802332152753734621[37] = 0;
   out_1802332152753734621[38] = 0;
   out_1802332152753734621[39] = 0;
   out_1802332152753734621[40] = 0;
   out_1802332152753734621[41] = 0;
   out_1802332152753734621[42] = 0;
   out_1802332152753734621[43] = 0;
   out_1802332152753734621[44] = 1;
   out_1802332152753734621[45] = 0;
   out_1802332152753734621[46] = 0;
   out_1802332152753734621[47] = 0;
   out_1802332152753734621[48] = 0;
   out_1802332152753734621[49] = 0;
   out_1802332152753734621[50] = 0;
   out_1802332152753734621[51] = 0;
   out_1802332152753734621[52] = 0;
   out_1802332152753734621[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4223042806110963609) {
  err_fun(nom_x, delta_x, out_4223042806110963609);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_8530086622469742933) {
  inv_err_fun(nom_x, true_x, out_8530086622469742933);
}
void pose_H_mod_fun(double *state, double *out_8909363854772424894) {
  H_mod_fun(state, out_8909363854772424894);
}
void pose_f_fun(double *state, double dt, double *out_1291447636833644141) {
  f_fun(state,  dt, out_1291447636833644141);
}
void pose_F_fun(double *state, double dt, double *out_2156602018501124106) {
  F_fun(state,  dt, out_2156602018501124106);
}
void pose_h_4(double *state, double *unused, double *out_6395852196578726056) {
  h_4(state, unused, out_6395852196578726056);
}
void pose_H_4(double *state, double *unused, double *out_5765573009093219150) {
  H_4(state, unused, out_5765573009093219150);
}
void pose_h_10(double *state, double *unused, double *out_7562508967147311156) {
  h_10(state, unused, out_7562508967147311156);
}
void pose_H_10(double *state, double *unused, double *out_4704156203817477126) {
  H_10(state, unused, out_4704156203817477126);
}
void pose_h_13(double *state, double *unused, double *out_4947379913658815439) {
  h_13(state, unused, out_4947379913658815439);
}
void pose_H_13(double *state, double *unused, double *out_2553299183760886349) {
  H_13(state, unused, out_2553299183760886349);
}
void pose_h_14(double *state, double *unused, double *out_4640800764138358777) {
  h_14(state, unused, out_4640800764138358777);
}
void pose_H_14(double *state, double *unused, double *out_1802332152753734621) {
  H_14(state, unused, out_1802332152753734621);
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
