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
void err_fun(double *nom_x, double *delta_x, double *out_5983304822532396966) {
   out_5983304822532396966[0] = delta_x[0] + nom_x[0];
   out_5983304822532396966[1] = delta_x[1] + nom_x[1];
   out_5983304822532396966[2] = delta_x[2] + nom_x[2];
   out_5983304822532396966[3] = delta_x[3] + nom_x[3];
   out_5983304822532396966[4] = delta_x[4] + nom_x[4];
   out_5983304822532396966[5] = delta_x[5] + nom_x[5];
   out_5983304822532396966[6] = delta_x[6] + nom_x[6];
   out_5983304822532396966[7] = delta_x[7] + nom_x[7];
   out_5983304822532396966[8] = delta_x[8] + nom_x[8];
   out_5983304822532396966[9] = delta_x[9] + nom_x[9];
   out_5983304822532396966[10] = delta_x[10] + nom_x[10];
   out_5983304822532396966[11] = delta_x[11] + nom_x[11];
   out_5983304822532396966[12] = delta_x[12] + nom_x[12];
   out_5983304822532396966[13] = delta_x[13] + nom_x[13];
   out_5983304822532396966[14] = delta_x[14] + nom_x[14];
   out_5983304822532396966[15] = delta_x[15] + nom_x[15];
   out_5983304822532396966[16] = delta_x[16] + nom_x[16];
   out_5983304822532396966[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6802128044019654079) {
   out_6802128044019654079[0] = -nom_x[0] + true_x[0];
   out_6802128044019654079[1] = -nom_x[1] + true_x[1];
   out_6802128044019654079[2] = -nom_x[2] + true_x[2];
   out_6802128044019654079[3] = -nom_x[3] + true_x[3];
   out_6802128044019654079[4] = -nom_x[4] + true_x[4];
   out_6802128044019654079[5] = -nom_x[5] + true_x[5];
   out_6802128044019654079[6] = -nom_x[6] + true_x[6];
   out_6802128044019654079[7] = -nom_x[7] + true_x[7];
   out_6802128044019654079[8] = -nom_x[8] + true_x[8];
   out_6802128044019654079[9] = -nom_x[9] + true_x[9];
   out_6802128044019654079[10] = -nom_x[10] + true_x[10];
   out_6802128044019654079[11] = -nom_x[11] + true_x[11];
   out_6802128044019654079[12] = -nom_x[12] + true_x[12];
   out_6802128044019654079[13] = -nom_x[13] + true_x[13];
   out_6802128044019654079[14] = -nom_x[14] + true_x[14];
   out_6802128044019654079[15] = -nom_x[15] + true_x[15];
   out_6802128044019654079[16] = -nom_x[16] + true_x[16];
   out_6802128044019654079[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3170132304237044244) {
   out_3170132304237044244[0] = 1.0;
   out_3170132304237044244[1] = 0.0;
   out_3170132304237044244[2] = 0.0;
   out_3170132304237044244[3] = 0.0;
   out_3170132304237044244[4] = 0.0;
   out_3170132304237044244[5] = 0.0;
   out_3170132304237044244[6] = 0.0;
   out_3170132304237044244[7] = 0.0;
   out_3170132304237044244[8] = 0.0;
   out_3170132304237044244[9] = 0.0;
   out_3170132304237044244[10] = 0.0;
   out_3170132304237044244[11] = 0.0;
   out_3170132304237044244[12] = 0.0;
   out_3170132304237044244[13] = 0.0;
   out_3170132304237044244[14] = 0.0;
   out_3170132304237044244[15] = 0.0;
   out_3170132304237044244[16] = 0.0;
   out_3170132304237044244[17] = 0.0;
   out_3170132304237044244[18] = 0.0;
   out_3170132304237044244[19] = 1.0;
   out_3170132304237044244[20] = 0.0;
   out_3170132304237044244[21] = 0.0;
   out_3170132304237044244[22] = 0.0;
   out_3170132304237044244[23] = 0.0;
   out_3170132304237044244[24] = 0.0;
   out_3170132304237044244[25] = 0.0;
   out_3170132304237044244[26] = 0.0;
   out_3170132304237044244[27] = 0.0;
   out_3170132304237044244[28] = 0.0;
   out_3170132304237044244[29] = 0.0;
   out_3170132304237044244[30] = 0.0;
   out_3170132304237044244[31] = 0.0;
   out_3170132304237044244[32] = 0.0;
   out_3170132304237044244[33] = 0.0;
   out_3170132304237044244[34] = 0.0;
   out_3170132304237044244[35] = 0.0;
   out_3170132304237044244[36] = 0.0;
   out_3170132304237044244[37] = 0.0;
   out_3170132304237044244[38] = 1.0;
   out_3170132304237044244[39] = 0.0;
   out_3170132304237044244[40] = 0.0;
   out_3170132304237044244[41] = 0.0;
   out_3170132304237044244[42] = 0.0;
   out_3170132304237044244[43] = 0.0;
   out_3170132304237044244[44] = 0.0;
   out_3170132304237044244[45] = 0.0;
   out_3170132304237044244[46] = 0.0;
   out_3170132304237044244[47] = 0.0;
   out_3170132304237044244[48] = 0.0;
   out_3170132304237044244[49] = 0.0;
   out_3170132304237044244[50] = 0.0;
   out_3170132304237044244[51] = 0.0;
   out_3170132304237044244[52] = 0.0;
   out_3170132304237044244[53] = 0.0;
   out_3170132304237044244[54] = 0.0;
   out_3170132304237044244[55] = 0.0;
   out_3170132304237044244[56] = 0.0;
   out_3170132304237044244[57] = 1.0;
   out_3170132304237044244[58] = 0.0;
   out_3170132304237044244[59] = 0.0;
   out_3170132304237044244[60] = 0.0;
   out_3170132304237044244[61] = 0.0;
   out_3170132304237044244[62] = 0.0;
   out_3170132304237044244[63] = 0.0;
   out_3170132304237044244[64] = 0.0;
   out_3170132304237044244[65] = 0.0;
   out_3170132304237044244[66] = 0.0;
   out_3170132304237044244[67] = 0.0;
   out_3170132304237044244[68] = 0.0;
   out_3170132304237044244[69] = 0.0;
   out_3170132304237044244[70] = 0.0;
   out_3170132304237044244[71] = 0.0;
   out_3170132304237044244[72] = 0.0;
   out_3170132304237044244[73] = 0.0;
   out_3170132304237044244[74] = 0.0;
   out_3170132304237044244[75] = 0.0;
   out_3170132304237044244[76] = 1.0;
   out_3170132304237044244[77] = 0.0;
   out_3170132304237044244[78] = 0.0;
   out_3170132304237044244[79] = 0.0;
   out_3170132304237044244[80] = 0.0;
   out_3170132304237044244[81] = 0.0;
   out_3170132304237044244[82] = 0.0;
   out_3170132304237044244[83] = 0.0;
   out_3170132304237044244[84] = 0.0;
   out_3170132304237044244[85] = 0.0;
   out_3170132304237044244[86] = 0.0;
   out_3170132304237044244[87] = 0.0;
   out_3170132304237044244[88] = 0.0;
   out_3170132304237044244[89] = 0.0;
   out_3170132304237044244[90] = 0.0;
   out_3170132304237044244[91] = 0.0;
   out_3170132304237044244[92] = 0.0;
   out_3170132304237044244[93] = 0.0;
   out_3170132304237044244[94] = 0.0;
   out_3170132304237044244[95] = 1.0;
   out_3170132304237044244[96] = 0.0;
   out_3170132304237044244[97] = 0.0;
   out_3170132304237044244[98] = 0.0;
   out_3170132304237044244[99] = 0.0;
   out_3170132304237044244[100] = 0.0;
   out_3170132304237044244[101] = 0.0;
   out_3170132304237044244[102] = 0.0;
   out_3170132304237044244[103] = 0.0;
   out_3170132304237044244[104] = 0.0;
   out_3170132304237044244[105] = 0.0;
   out_3170132304237044244[106] = 0.0;
   out_3170132304237044244[107] = 0.0;
   out_3170132304237044244[108] = 0.0;
   out_3170132304237044244[109] = 0.0;
   out_3170132304237044244[110] = 0.0;
   out_3170132304237044244[111] = 0.0;
   out_3170132304237044244[112] = 0.0;
   out_3170132304237044244[113] = 0.0;
   out_3170132304237044244[114] = 1.0;
   out_3170132304237044244[115] = 0.0;
   out_3170132304237044244[116] = 0.0;
   out_3170132304237044244[117] = 0.0;
   out_3170132304237044244[118] = 0.0;
   out_3170132304237044244[119] = 0.0;
   out_3170132304237044244[120] = 0.0;
   out_3170132304237044244[121] = 0.0;
   out_3170132304237044244[122] = 0.0;
   out_3170132304237044244[123] = 0.0;
   out_3170132304237044244[124] = 0.0;
   out_3170132304237044244[125] = 0.0;
   out_3170132304237044244[126] = 0.0;
   out_3170132304237044244[127] = 0.0;
   out_3170132304237044244[128] = 0.0;
   out_3170132304237044244[129] = 0.0;
   out_3170132304237044244[130] = 0.0;
   out_3170132304237044244[131] = 0.0;
   out_3170132304237044244[132] = 0.0;
   out_3170132304237044244[133] = 1.0;
   out_3170132304237044244[134] = 0.0;
   out_3170132304237044244[135] = 0.0;
   out_3170132304237044244[136] = 0.0;
   out_3170132304237044244[137] = 0.0;
   out_3170132304237044244[138] = 0.0;
   out_3170132304237044244[139] = 0.0;
   out_3170132304237044244[140] = 0.0;
   out_3170132304237044244[141] = 0.0;
   out_3170132304237044244[142] = 0.0;
   out_3170132304237044244[143] = 0.0;
   out_3170132304237044244[144] = 0.0;
   out_3170132304237044244[145] = 0.0;
   out_3170132304237044244[146] = 0.0;
   out_3170132304237044244[147] = 0.0;
   out_3170132304237044244[148] = 0.0;
   out_3170132304237044244[149] = 0.0;
   out_3170132304237044244[150] = 0.0;
   out_3170132304237044244[151] = 0.0;
   out_3170132304237044244[152] = 1.0;
   out_3170132304237044244[153] = 0.0;
   out_3170132304237044244[154] = 0.0;
   out_3170132304237044244[155] = 0.0;
   out_3170132304237044244[156] = 0.0;
   out_3170132304237044244[157] = 0.0;
   out_3170132304237044244[158] = 0.0;
   out_3170132304237044244[159] = 0.0;
   out_3170132304237044244[160] = 0.0;
   out_3170132304237044244[161] = 0.0;
   out_3170132304237044244[162] = 0.0;
   out_3170132304237044244[163] = 0.0;
   out_3170132304237044244[164] = 0.0;
   out_3170132304237044244[165] = 0.0;
   out_3170132304237044244[166] = 0.0;
   out_3170132304237044244[167] = 0.0;
   out_3170132304237044244[168] = 0.0;
   out_3170132304237044244[169] = 0.0;
   out_3170132304237044244[170] = 0.0;
   out_3170132304237044244[171] = 1.0;
   out_3170132304237044244[172] = 0.0;
   out_3170132304237044244[173] = 0.0;
   out_3170132304237044244[174] = 0.0;
   out_3170132304237044244[175] = 0.0;
   out_3170132304237044244[176] = 0.0;
   out_3170132304237044244[177] = 0.0;
   out_3170132304237044244[178] = 0.0;
   out_3170132304237044244[179] = 0.0;
   out_3170132304237044244[180] = 0.0;
   out_3170132304237044244[181] = 0.0;
   out_3170132304237044244[182] = 0.0;
   out_3170132304237044244[183] = 0.0;
   out_3170132304237044244[184] = 0.0;
   out_3170132304237044244[185] = 0.0;
   out_3170132304237044244[186] = 0.0;
   out_3170132304237044244[187] = 0.0;
   out_3170132304237044244[188] = 0.0;
   out_3170132304237044244[189] = 0.0;
   out_3170132304237044244[190] = 1.0;
   out_3170132304237044244[191] = 0.0;
   out_3170132304237044244[192] = 0.0;
   out_3170132304237044244[193] = 0.0;
   out_3170132304237044244[194] = 0.0;
   out_3170132304237044244[195] = 0.0;
   out_3170132304237044244[196] = 0.0;
   out_3170132304237044244[197] = 0.0;
   out_3170132304237044244[198] = 0.0;
   out_3170132304237044244[199] = 0.0;
   out_3170132304237044244[200] = 0.0;
   out_3170132304237044244[201] = 0.0;
   out_3170132304237044244[202] = 0.0;
   out_3170132304237044244[203] = 0.0;
   out_3170132304237044244[204] = 0.0;
   out_3170132304237044244[205] = 0.0;
   out_3170132304237044244[206] = 0.0;
   out_3170132304237044244[207] = 0.0;
   out_3170132304237044244[208] = 0.0;
   out_3170132304237044244[209] = 1.0;
   out_3170132304237044244[210] = 0.0;
   out_3170132304237044244[211] = 0.0;
   out_3170132304237044244[212] = 0.0;
   out_3170132304237044244[213] = 0.0;
   out_3170132304237044244[214] = 0.0;
   out_3170132304237044244[215] = 0.0;
   out_3170132304237044244[216] = 0.0;
   out_3170132304237044244[217] = 0.0;
   out_3170132304237044244[218] = 0.0;
   out_3170132304237044244[219] = 0.0;
   out_3170132304237044244[220] = 0.0;
   out_3170132304237044244[221] = 0.0;
   out_3170132304237044244[222] = 0.0;
   out_3170132304237044244[223] = 0.0;
   out_3170132304237044244[224] = 0.0;
   out_3170132304237044244[225] = 0.0;
   out_3170132304237044244[226] = 0.0;
   out_3170132304237044244[227] = 0.0;
   out_3170132304237044244[228] = 1.0;
   out_3170132304237044244[229] = 0.0;
   out_3170132304237044244[230] = 0.0;
   out_3170132304237044244[231] = 0.0;
   out_3170132304237044244[232] = 0.0;
   out_3170132304237044244[233] = 0.0;
   out_3170132304237044244[234] = 0.0;
   out_3170132304237044244[235] = 0.0;
   out_3170132304237044244[236] = 0.0;
   out_3170132304237044244[237] = 0.0;
   out_3170132304237044244[238] = 0.0;
   out_3170132304237044244[239] = 0.0;
   out_3170132304237044244[240] = 0.0;
   out_3170132304237044244[241] = 0.0;
   out_3170132304237044244[242] = 0.0;
   out_3170132304237044244[243] = 0.0;
   out_3170132304237044244[244] = 0.0;
   out_3170132304237044244[245] = 0.0;
   out_3170132304237044244[246] = 0.0;
   out_3170132304237044244[247] = 1.0;
   out_3170132304237044244[248] = 0.0;
   out_3170132304237044244[249] = 0.0;
   out_3170132304237044244[250] = 0.0;
   out_3170132304237044244[251] = 0.0;
   out_3170132304237044244[252] = 0.0;
   out_3170132304237044244[253] = 0.0;
   out_3170132304237044244[254] = 0.0;
   out_3170132304237044244[255] = 0.0;
   out_3170132304237044244[256] = 0.0;
   out_3170132304237044244[257] = 0.0;
   out_3170132304237044244[258] = 0.0;
   out_3170132304237044244[259] = 0.0;
   out_3170132304237044244[260] = 0.0;
   out_3170132304237044244[261] = 0.0;
   out_3170132304237044244[262] = 0.0;
   out_3170132304237044244[263] = 0.0;
   out_3170132304237044244[264] = 0.0;
   out_3170132304237044244[265] = 0.0;
   out_3170132304237044244[266] = 1.0;
   out_3170132304237044244[267] = 0.0;
   out_3170132304237044244[268] = 0.0;
   out_3170132304237044244[269] = 0.0;
   out_3170132304237044244[270] = 0.0;
   out_3170132304237044244[271] = 0.0;
   out_3170132304237044244[272] = 0.0;
   out_3170132304237044244[273] = 0.0;
   out_3170132304237044244[274] = 0.0;
   out_3170132304237044244[275] = 0.0;
   out_3170132304237044244[276] = 0.0;
   out_3170132304237044244[277] = 0.0;
   out_3170132304237044244[278] = 0.0;
   out_3170132304237044244[279] = 0.0;
   out_3170132304237044244[280] = 0.0;
   out_3170132304237044244[281] = 0.0;
   out_3170132304237044244[282] = 0.0;
   out_3170132304237044244[283] = 0.0;
   out_3170132304237044244[284] = 0.0;
   out_3170132304237044244[285] = 1.0;
   out_3170132304237044244[286] = 0.0;
   out_3170132304237044244[287] = 0.0;
   out_3170132304237044244[288] = 0.0;
   out_3170132304237044244[289] = 0.0;
   out_3170132304237044244[290] = 0.0;
   out_3170132304237044244[291] = 0.0;
   out_3170132304237044244[292] = 0.0;
   out_3170132304237044244[293] = 0.0;
   out_3170132304237044244[294] = 0.0;
   out_3170132304237044244[295] = 0.0;
   out_3170132304237044244[296] = 0.0;
   out_3170132304237044244[297] = 0.0;
   out_3170132304237044244[298] = 0.0;
   out_3170132304237044244[299] = 0.0;
   out_3170132304237044244[300] = 0.0;
   out_3170132304237044244[301] = 0.0;
   out_3170132304237044244[302] = 0.0;
   out_3170132304237044244[303] = 0.0;
   out_3170132304237044244[304] = 1.0;
   out_3170132304237044244[305] = 0.0;
   out_3170132304237044244[306] = 0.0;
   out_3170132304237044244[307] = 0.0;
   out_3170132304237044244[308] = 0.0;
   out_3170132304237044244[309] = 0.0;
   out_3170132304237044244[310] = 0.0;
   out_3170132304237044244[311] = 0.0;
   out_3170132304237044244[312] = 0.0;
   out_3170132304237044244[313] = 0.0;
   out_3170132304237044244[314] = 0.0;
   out_3170132304237044244[315] = 0.0;
   out_3170132304237044244[316] = 0.0;
   out_3170132304237044244[317] = 0.0;
   out_3170132304237044244[318] = 0.0;
   out_3170132304237044244[319] = 0.0;
   out_3170132304237044244[320] = 0.0;
   out_3170132304237044244[321] = 0.0;
   out_3170132304237044244[322] = 0.0;
   out_3170132304237044244[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8255079778207779351) {
   out_8255079778207779351[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8255079778207779351[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8255079778207779351[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8255079778207779351[3] = dt*state[12] + state[3];
   out_8255079778207779351[4] = dt*state[13] + state[4];
   out_8255079778207779351[5] = dt*state[14] + state[5];
   out_8255079778207779351[6] = state[6];
   out_8255079778207779351[7] = state[7];
   out_8255079778207779351[8] = state[8];
   out_8255079778207779351[9] = state[9];
   out_8255079778207779351[10] = state[10];
   out_8255079778207779351[11] = state[11];
   out_8255079778207779351[12] = state[12];
   out_8255079778207779351[13] = state[13];
   out_8255079778207779351[14] = state[14];
   out_8255079778207779351[15] = state[15];
   out_8255079778207779351[16] = state[16];
   out_8255079778207779351[17] = state[17];
}
void F_fun(double *state, double dt, double *out_4238693480342293986) {
   out_4238693480342293986[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4238693480342293986[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4238693480342293986[2] = 0;
   out_4238693480342293986[3] = 0;
   out_4238693480342293986[4] = 0;
   out_4238693480342293986[5] = 0;
   out_4238693480342293986[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4238693480342293986[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4238693480342293986[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_4238693480342293986[9] = 0;
   out_4238693480342293986[10] = 0;
   out_4238693480342293986[11] = 0;
   out_4238693480342293986[12] = 0;
   out_4238693480342293986[13] = 0;
   out_4238693480342293986[14] = 0;
   out_4238693480342293986[15] = 0;
   out_4238693480342293986[16] = 0;
   out_4238693480342293986[17] = 0;
   out_4238693480342293986[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4238693480342293986[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4238693480342293986[20] = 0;
   out_4238693480342293986[21] = 0;
   out_4238693480342293986[22] = 0;
   out_4238693480342293986[23] = 0;
   out_4238693480342293986[24] = 0;
   out_4238693480342293986[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4238693480342293986[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_4238693480342293986[27] = 0;
   out_4238693480342293986[28] = 0;
   out_4238693480342293986[29] = 0;
   out_4238693480342293986[30] = 0;
   out_4238693480342293986[31] = 0;
   out_4238693480342293986[32] = 0;
   out_4238693480342293986[33] = 0;
   out_4238693480342293986[34] = 0;
   out_4238693480342293986[35] = 0;
   out_4238693480342293986[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4238693480342293986[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4238693480342293986[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4238693480342293986[39] = 0;
   out_4238693480342293986[40] = 0;
   out_4238693480342293986[41] = 0;
   out_4238693480342293986[42] = 0;
   out_4238693480342293986[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4238693480342293986[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_4238693480342293986[45] = 0;
   out_4238693480342293986[46] = 0;
   out_4238693480342293986[47] = 0;
   out_4238693480342293986[48] = 0;
   out_4238693480342293986[49] = 0;
   out_4238693480342293986[50] = 0;
   out_4238693480342293986[51] = 0;
   out_4238693480342293986[52] = 0;
   out_4238693480342293986[53] = 0;
   out_4238693480342293986[54] = 0;
   out_4238693480342293986[55] = 0;
   out_4238693480342293986[56] = 0;
   out_4238693480342293986[57] = 1;
   out_4238693480342293986[58] = 0;
   out_4238693480342293986[59] = 0;
   out_4238693480342293986[60] = 0;
   out_4238693480342293986[61] = 0;
   out_4238693480342293986[62] = 0;
   out_4238693480342293986[63] = 0;
   out_4238693480342293986[64] = 0;
   out_4238693480342293986[65] = 0;
   out_4238693480342293986[66] = dt;
   out_4238693480342293986[67] = 0;
   out_4238693480342293986[68] = 0;
   out_4238693480342293986[69] = 0;
   out_4238693480342293986[70] = 0;
   out_4238693480342293986[71] = 0;
   out_4238693480342293986[72] = 0;
   out_4238693480342293986[73] = 0;
   out_4238693480342293986[74] = 0;
   out_4238693480342293986[75] = 0;
   out_4238693480342293986[76] = 1;
   out_4238693480342293986[77] = 0;
   out_4238693480342293986[78] = 0;
   out_4238693480342293986[79] = 0;
   out_4238693480342293986[80] = 0;
   out_4238693480342293986[81] = 0;
   out_4238693480342293986[82] = 0;
   out_4238693480342293986[83] = 0;
   out_4238693480342293986[84] = 0;
   out_4238693480342293986[85] = dt;
   out_4238693480342293986[86] = 0;
   out_4238693480342293986[87] = 0;
   out_4238693480342293986[88] = 0;
   out_4238693480342293986[89] = 0;
   out_4238693480342293986[90] = 0;
   out_4238693480342293986[91] = 0;
   out_4238693480342293986[92] = 0;
   out_4238693480342293986[93] = 0;
   out_4238693480342293986[94] = 0;
   out_4238693480342293986[95] = 1;
   out_4238693480342293986[96] = 0;
   out_4238693480342293986[97] = 0;
   out_4238693480342293986[98] = 0;
   out_4238693480342293986[99] = 0;
   out_4238693480342293986[100] = 0;
   out_4238693480342293986[101] = 0;
   out_4238693480342293986[102] = 0;
   out_4238693480342293986[103] = 0;
   out_4238693480342293986[104] = dt;
   out_4238693480342293986[105] = 0;
   out_4238693480342293986[106] = 0;
   out_4238693480342293986[107] = 0;
   out_4238693480342293986[108] = 0;
   out_4238693480342293986[109] = 0;
   out_4238693480342293986[110] = 0;
   out_4238693480342293986[111] = 0;
   out_4238693480342293986[112] = 0;
   out_4238693480342293986[113] = 0;
   out_4238693480342293986[114] = 1;
   out_4238693480342293986[115] = 0;
   out_4238693480342293986[116] = 0;
   out_4238693480342293986[117] = 0;
   out_4238693480342293986[118] = 0;
   out_4238693480342293986[119] = 0;
   out_4238693480342293986[120] = 0;
   out_4238693480342293986[121] = 0;
   out_4238693480342293986[122] = 0;
   out_4238693480342293986[123] = 0;
   out_4238693480342293986[124] = 0;
   out_4238693480342293986[125] = 0;
   out_4238693480342293986[126] = 0;
   out_4238693480342293986[127] = 0;
   out_4238693480342293986[128] = 0;
   out_4238693480342293986[129] = 0;
   out_4238693480342293986[130] = 0;
   out_4238693480342293986[131] = 0;
   out_4238693480342293986[132] = 0;
   out_4238693480342293986[133] = 1;
   out_4238693480342293986[134] = 0;
   out_4238693480342293986[135] = 0;
   out_4238693480342293986[136] = 0;
   out_4238693480342293986[137] = 0;
   out_4238693480342293986[138] = 0;
   out_4238693480342293986[139] = 0;
   out_4238693480342293986[140] = 0;
   out_4238693480342293986[141] = 0;
   out_4238693480342293986[142] = 0;
   out_4238693480342293986[143] = 0;
   out_4238693480342293986[144] = 0;
   out_4238693480342293986[145] = 0;
   out_4238693480342293986[146] = 0;
   out_4238693480342293986[147] = 0;
   out_4238693480342293986[148] = 0;
   out_4238693480342293986[149] = 0;
   out_4238693480342293986[150] = 0;
   out_4238693480342293986[151] = 0;
   out_4238693480342293986[152] = 1;
   out_4238693480342293986[153] = 0;
   out_4238693480342293986[154] = 0;
   out_4238693480342293986[155] = 0;
   out_4238693480342293986[156] = 0;
   out_4238693480342293986[157] = 0;
   out_4238693480342293986[158] = 0;
   out_4238693480342293986[159] = 0;
   out_4238693480342293986[160] = 0;
   out_4238693480342293986[161] = 0;
   out_4238693480342293986[162] = 0;
   out_4238693480342293986[163] = 0;
   out_4238693480342293986[164] = 0;
   out_4238693480342293986[165] = 0;
   out_4238693480342293986[166] = 0;
   out_4238693480342293986[167] = 0;
   out_4238693480342293986[168] = 0;
   out_4238693480342293986[169] = 0;
   out_4238693480342293986[170] = 0;
   out_4238693480342293986[171] = 1;
   out_4238693480342293986[172] = 0;
   out_4238693480342293986[173] = 0;
   out_4238693480342293986[174] = 0;
   out_4238693480342293986[175] = 0;
   out_4238693480342293986[176] = 0;
   out_4238693480342293986[177] = 0;
   out_4238693480342293986[178] = 0;
   out_4238693480342293986[179] = 0;
   out_4238693480342293986[180] = 0;
   out_4238693480342293986[181] = 0;
   out_4238693480342293986[182] = 0;
   out_4238693480342293986[183] = 0;
   out_4238693480342293986[184] = 0;
   out_4238693480342293986[185] = 0;
   out_4238693480342293986[186] = 0;
   out_4238693480342293986[187] = 0;
   out_4238693480342293986[188] = 0;
   out_4238693480342293986[189] = 0;
   out_4238693480342293986[190] = 1;
   out_4238693480342293986[191] = 0;
   out_4238693480342293986[192] = 0;
   out_4238693480342293986[193] = 0;
   out_4238693480342293986[194] = 0;
   out_4238693480342293986[195] = 0;
   out_4238693480342293986[196] = 0;
   out_4238693480342293986[197] = 0;
   out_4238693480342293986[198] = 0;
   out_4238693480342293986[199] = 0;
   out_4238693480342293986[200] = 0;
   out_4238693480342293986[201] = 0;
   out_4238693480342293986[202] = 0;
   out_4238693480342293986[203] = 0;
   out_4238693480342293986[204] = 0;
   out_4238693480342293986[205] = 0;
   out_4238693480342293986[206] = 0;
   out_4238693480342293986[207] = 0;
   out_4238693480342293986[208] = 0;
   out_4238693480342293986[209] = 1;
   out_4238693480342293986[210] = 0;
   out_4238693480342293986[211] = 0;
   out_4238693480342293986[212] = 0;
   out_4238693480342293986[213] = 0;
   out_4238693480342293986[214] = 0;
   out_4238693480342293986[215] = 0;
   out_4238693480342293986[216] = 0;
   out_4238693480342293986[217] = 0;
   out_4238693480342293986[218] = 0;
   out_4238693480342293986[219] = 0;
   out_4238693480342293986[220] = 0;
   out_4238693480342293986[221] = 0;
   out_4238693480342293986[222] = 0;
   out_4238693480342293986[223] = 0;
   out_4238693480342293986[224] = 0;
   out_4238693480342293986[225] = 0;
   out_4238693480342293986[226] = 0;
   out_4238693480342293986[227] = 0;
   out_4238693480342293986[228] = 1;
   out_4238693480342293986[229] = 0;
   out_4238693480342293986[230] = 0;
   out_4238693480342293986[231] = 0;
   out_4238693480342293986[232] = 0;
   out_4238693480342293986[233] = 0;
   out_4238693480342293986[234] = 0;
   out_4238693480342293986[235] = 0;
   out_4238693480342293986[236] = 0;
   out_4238693480342293986[237] = 0;
   out_4238693480342293986[238] = 0;
   out_4238693480342293986[239] = 0;
   out_4238693480342293986[240] = 0;
   out_4238693480342293986[241] = 0;
   out_4238693480342293986[242] = 0;
   out_4238693480342293986[243] = 0;
   out_4238693480342293986[244] = 0;
   out_4238693480342293986[245] = 0;
   out_4238693480342293986[246] = 0;
   out_4238693480342293986[247] = 1;
   out_4238693480342293986[248] = 0;
   out_4238693480342293986[249] = 0;
   out_4238693480342293986[250] = 0;
   out_4238693480342293986[251] = 0;
   out_4238693480342293986[252] = 0;
   out_4238693480342293986[253] = 0;
   out_4238693480342293986[254] = 0;
   out_4238693480342293986[255] = 0;
   out_4238693480342293986[256] = 0;
   out_4238693480342293986[257] = 0;
   out_4238693480342293986[258] = 0;
   out_4238693480342293986[259] = 0;
   out_4238693480342293986[260] = 0;
   out_4238693480342293986[261] = 0;
   out_4238693480342293986[262] = 0;
   out_4238693480342293986[263] = 0;
   out_4238693480342293986[264] = 0;
   out_4238693480342293986[265] = 0;
   out_4238693480342293986[266] = 1;
   out_4238693480342293986[267] = 0;
   out_4238693480342293986[268] = 0;
   out_4238693480342293986[269] = 0;
   out_4238693480342293986[270] = 0;
   out_4238693480342293986[271] = 0;
   out_4238693480342293986[272] = 0;
   out_4238693480342293986[273] = 0;
   out_4238693480342293986[274] = 0;
   out_4238693480342293986[275] = 0;
   out_4238693480342293986[276] = 0;
   out_4238693480342293986[277] = 0;
   out_4238693480342293986[278] = 0;
   out_4238693480342293986[279] = 0;
   out_4238693480342293986[280] = 0;
   out_4238693480342293986[281] = 0;
   out_4238693480342293986[282] = 0;
   out_4238693480342293986[283] = 0;
   out_4238693480342293986[284] = 0;
   out_4238693480342293986[285] = 1;
   out_4238693480342293986[286] = 0;
   out_4238693480342293986[287] = 0;
   out_4238693480342293986[288] = 0;
   out_4238693480342293986[289] = 0;
   out_4238693480342293986[290] = 0;
   out_4238693480342293986[291] = 0;
   out_4238693480342293986[292] = 0;
   out_4238693480342293986[293] = 0;
   out_4238693480342293986[294] = 0;
   out_4238693480342293986[295] = 0;
   out_4238693480342293986[296] = 0;
   out_4238693480342293986[297] = 0;
   out_4238693480342293986[298] = 0;
   out_4238693480342293986[299] = 0;
   out_4238693480342293986[300] = 0;
   out_4238693480342293986[301] = 0;
   out_4238693480342293986[302] = 0;
   out_4238693480342293986[303] = 0;
   out_4238693480342293986[304] = 1;
   out_4238693480342293986[305] = 0;
   out_4238693480342293986[306] = 0;
   out_4238693480342293986[307] = 0;
   out_4238693480342293986[308] = 0;
   out_4238693480342293986[309] = 0;
   out_4238693480342293986[310] = 0;
   out_4238693480342293986[311] = 0;
   out_4238693480342293986[312] = 0;
   out_4238693480342293986[313] = 0;
   out_4238693480342293986[314] = 0;
   out_4238693480342293986[315] = 0;
   out_4238693480342293986[316] = 0;
   out_4238693480342293986[317] = 0;
   out_4238693480342293986[318] = 0;
   out_4238693480342293986[319] = 0;
   out_4238693480342293986[320] = 0;
   out_4238693480342293986[321] = 0;
   out_4238693480342293986[322] = 0;
   out_4238693480342293986[323] = 1;
}
void h_4(double *state, double *unused, double *out_2471379555464088728) {
   out_2471379555464088728[0] = state[6] + state[9];
   out_2471379555464088728[1] = state[7] + state[10];
   out_2471379555464088728[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8322650689276124979) {
   out_8322650689276124979[0] = 0;
   out_8322650689276124979[1] = 0;
   out_8322650689276124979[2] = 0;
   out_8322650689276124979[3] = 0;
   out_8322650689276124979[4] = 0;
   out_8322650689276124979[5] = 0;
   out_8322650689276124979[6] = 1;
   out_8322650689276124979[7] = 0;
   out_8322650689276124979[8] = 0;
   out_8322650689276124979[9] = 1;
   out_8322650689276124979[10] = 0;
   out_8322650689276124979[11] = 0;
   out_8322650689276124979[12] = 0;
   out_8322650689276124979[13] = 0;
   out_8322650689276124979[14] = 0;
   out_8322650689276124979[15] = 0;
   out_8322650689276124979[16] = 0;
   out_8322650689276124979[17] = 0;
   out_8322650689276124979[18] = 0;
   out_8322650689276124979[19] = 0;
   out_8322650689276124979[20] = 0;
   out_8322650689276124979[21] = 0;
   out_8322650689276124979[22] = 0;
   out_8322650689276124979[23] = 0;
   out_8322650689276124979[24] = 0;
   out_8322650689276124979[25] = 1;
   out_8322650689276124979[26] = 0;
   out_8322650689276124979[27] = 0;
   out_8322650689276124979[28] = 1;
   out_8322650689276124979[29] = 0;
   out_8322650689276124979[30] = 0;
   out_8322650689276124979[31] = 0;
   out_8322650689276124979[32] = 0;
   out_8322650689276124979[33] = 0;
   out_8322650689276124979[34] = 0;
   out_8322650689276124979[35] = 0;
   out_8322650689276124979[36] = 0;
   out_8322650689276124979[37] = 0;
   out_8322650689276124979[38] = 0;
   out_8322650689276124979[39] = 0;
   out_8322650689276124979[40] = 0;
   out_8322650689276124979[41] = 0;
   out_8322650689276124979[42] = 0;
   out_8322650689276124979[43] = 0;
   out_8322650689276124979[44] = 1;
   out_8322650689276124979[45] = 0;
   out_8322650689276124979[46] = 0;
   out_8322650689276124979[47] = 1;
   out_8322650689276124979[48] = 0;
   out_8322650689276124979[49] = 0;
   out_8322650689276124979[50] = 0;
   out_8322650689276124979[51] = 0;
   out_8322650689276124979[52] = 0;
   out_8322650689276124979[53] = 0;
}
void h_10(double *state, double *unused, double *out_5249786927742937080) {
   out_5249786927742937080[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5249786927742937080[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5249786927742937080[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_8433765414018862422) {
   out_8433765414018862422[0] = 0;
   out_8433765414018862422[1] = 9.8100000000000005*cos(state[1]);
   out_8433765414018862422[2] = 0;
   out_8433765414018862422[3] = 0;
   out_8433765414018862422[4] = -state[8];
   out_8433765414018862422[5] = state[7];
   out_8433765414018862422[6] = 0;
   out_8433765414018862422[7] = state[5];
   out_8433765414018862422[8] = -state[4];
   out_8433765414018862422[9] = 0;
   out_8433765414018862422[10] = 0;
   out_8433765414018862422[11] = 0;
   out_8433765414018862422[12] = 1;
   out_8433765414018862422[13] = 0;
   out_8433765414018862422[14] = 0;
   out_8433765414018862422[15] = 1;
   out_8433765414018862422[16] = 0;
   out_8433765414018862422[17] = 0;
   out_8433765414018862422[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_8433765414018862422[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_8433765414018862422[20] = 0;
   out_8433765414018862422[21] = state[8];
   out_8433765414018862422[22] = 0;
   out_8433765414018862422[23] = -state[6];
   out_8433765414018862422[24] = -state[5];
   out_8433765414018862422[25] = 0;
   out_8433765414018862422[26] = state[3];
   out_8433765414018862422[27] = 0;
   out_8433765414018862422[28] = 0;
   out_8433765414018862422[29] = 0;
   out_8433765414018862422[30] = 0;
   out_8433765414018862422[31] = 1;
   out_8433765414018862422[32] = 0;
   out_8433765414018862422[33] = 0;
   out_8433765414018862422[34] = 1;
   out_8433765414018862422[35] = 0;
   out_8433765414018862422[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_8433765414018862422[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_8433765414018862422[38] = 0;
   out_8433765414018862422[39] = -state[7];
   out_8433765414018862422[40] = state[6];
   out_8433765414018862422[41] = 0;
   out_8433765414018862422[42] = state[4];
   out_8433765414018862422[43] = -state[3];
   out_8433765414018862422[44] = 0;
   out_8433765414018862422[45] = 0;
   out_8433765414018862422[46] = 0;
   out_8433765414018862422[47] = 0;
   out_8433765414018862422[48] = 0;
   out_8433765414018862422[49] = 0;
   out_8433765414018862422[50] = 1;
   out_8433765414018862422[51] = 0;
   out_8433765414018862422[52] = 0;
   out_8433765414018862422[53] = 1;
}
void h_13(double *state, double *unused, double *out_3320787694222680609) {
   out_3320787694222680609[0] = state[3];
   out_3320787694222680609[1] = state[4];
   out_3320787694222680609[2] = state[5];
}
void H_13(double *state, double *unused, double *out_6911819559101093836) {
   out_6911819559101093836[0] = 0;
   out_6911819559101093836[1] = 0;
   out_6911819559101093836[2] = 0;
   out_6911819559101093836[3] = 1;
   out_6911819559101093836[4] = 0;
   out_6911819559101093836[5] = 0;
   out_6911819559101093836[6] = 0;
   out_6911819559101093836[7] = 0;
   out_6911819559101093836[8] = 0;
   out_6911819559101093836[9] = 0;
   out_6911819559101093836[10] = 0;
   out_6911819559101093836[11] = 0;
   out_6911819559101093836[12] = 0;
   out_6911819559101093836[13] = 0;
   out_6911819559101093836[14] = 0;
   out_6911819559101093836[15] = 0;
   out_6911819559101093836[16] = 0;
   out_6911819559101093836[17] = 0;
   out_6911819559101093836[18] = 0;
   out_6911819559101093836[19] = 0;
   out_6911819559101093836[20] = 0;
   out_6911819559101093836[21] = 0;
   out_6911819559101093836[22] = 1;
   out_6911819559101093836[23] = 0;
   out_6911819559101093836[24] = 0;
   out_6911819559101093836[25] = 0;
   out_6911819559101093836[26] = 0;
   out_6911819559101093836[27] = 0;
   out_6911819559101093836[28] = 0;
   out_6911819559101093836[29] = 0;
   out_6911819559101093836[30] = 0;
   out_6911819559101093836[31] = 0;
   out_6911819559101093836[32] = 0;
   out_6911819559101093836[33] = 0;
   out_6911819559101093836[34] = 0;
   out_6911819559101093836[35] = 0;
   out_6911819559101093836[36] = 0;
   out_6911819559101093836[37] = 0;
   out_6911819559101093836[38] = 0;
   out_6911819559101093836[39] = 0;
   out_6911819559101093836[40] = 0;
   out_6911819559101093836[41] = 1;
   out_6911819559101093836[42] = 0;
   out_6911819559101093836[43] = 0;
   out_6911819559101093836[44] = 0;
   out_6911819559101093836[45] = 0;
   out_6911819559101093836[46] = 0;
   out_6911819559101093836[47] = 0;
   out_6911819559101093836[48] = 0;
   out_6911819559101093836[49] = 0;
   out_6911819559101093836[50] = 0;
   out_6911819559101093836[51] = 0;
   out_6911819559101093836[52] = 0;
   out_6911819559101093836[53] = 0;
}
void h_14(double *state, double *unused, double *out_7880969684345092326) {
   out_7880969684345092326[0] = state[6];
   out_7880969684345092326[1] = state[7];
   out_7880969684345092326[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6160852528093942108) {
   out_6160852528093942108[0] = 0;
   out_6160852528093942108[1] = 0;
   out_6160852528093942108[2] = 0;
   out_6160852528093942108[3] = 0;
   out_6160852528093942108[4] = 0;
   out_6160852528093942108[5] = 0;
   out_6160852528093942108[6] = 1;
   out_6160852528093942108[7] = 0;
   out_6160852528093942108[8] = 0;
   out_6160852528093942108[9] = 0;
   out_6160852528093942108[10] = 0;
   out_6160852528093942108[11] = 0;
   out_6160852528093942108[12] = 0;
   out_6160852528093942108[13] = 0;
   out_6160852528093942108[14] = 0;
   out_6160852528093942108[15] = 0;
   out_6160852528093942108[16] = 0;
   out_6160852528093942108[17] = 0;
   out_6160852528093942108[18] = 0;
   out_6160852528093942108[19] = 0;
   out_6160852528093942108[20] = 0;
   out_6160852528093942108[21] = 0;
   out_6160852528093942108[22] = 0;
   out_6160852528093942108[23] = 0;
   out_6160852528093942108[24] = 0;
   out_6160852528093942108[25] = 1;
   out_6160852528093942108[26] = 0;
   out_6160852528093942108[27] = 0;
   out_6160852528093942108[28] = 0;
   out_6160852528093942108[29] = 0;
   out_6160852528093942108[30] = 0;
   out_6160852528093942108[31] = 0;
   out_6160852528093942108[32] = 0;
   out_6160852528093942108[33] = 0;
   out_6160852528093942108[34] = 0;
   out_6160852528093942108[35] = 0;
   out_6160852528093942108[36] = 0;
   out_6160852528093942108[37] = 0;
   out_6160852528093942108[38] = 0;
   out_6160852528093942108[39] = 0;
   out_6160852528093942108[40] = 0;
   out_6160852528093942108[41] = 0;
   out_6160852528093942108[42] = 0;
   out_6160852528093942108[43] = 0;
   out_6160852528093942108[44] = 1;
   out_6160852528093942108[45] = 0;
   out_6160852528093942108[46] = 0;
   out_6160852528093942108[47] = 0;
   out_6160852528093942108[48] = 0;
   out_6160852528093942108[49] = 0;
   out_6160852528093942108[50] = 0;
   out_6160852528093942108[51] = 0;
   out_6160852528093942108[52] = 0;
   out_6160852528093942108[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_5983304822532396966) {
  err_fun(nom_x, delta_x, out_5983304822532396966);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_6802128044019654079) {
  inv_err_fun(nom_x, true_x, out_6802128044019654079);
}
void pose_H_mod_fun(double *state, double *out_3170132304237044244) {
  H_mod_fun(state, out_3170132304237044244);
}
void pose_f_fun(double *state, double dt, double *out_8255079778207779351) {
  f_fun(state,  dt, out_8255079778207779351);
}
void pose_F_fun(double *state, double dt, double *out_4238693480342293986) {
  F_fun(state,  dt, out_4238693480342293986);
}
void pose_h_4(double *state, double *unused, double *out_2471379555464088728) {
  h_4(state, unused, out_2471379555464088728);
}
void pose_H_4(double *state, double *unused, double *out_8322650689276124979) {
  H_4(state, unused, out_8322650689276124979);
}
void pose_h_10(double *state, double *unused, double *out_5249786927742937080) {
  h_10(state, unused, out_5249786927742937080);
}
void pose_H_10(double *state, double *unused, double *out_8433765414018862422) {
  H_10(state, unused, out_8433765414018862422);
}
void pose_h_13(double *state, double *unused, double *out_3320787694222680609) {
  h_13(state, unused, out_3320787694222680609);
}
void pose_H_13(double *state, double *unused, double *out_6911819559101093836) {
  H_13(state, unused, out_6911819559101093836);
}
void pose_h_14(double *state, double *unused, double *out_7880969684345092326) {
  h_14(state, unused, out_7880969684345092326);
}
void pose_H_14(double *state, double *unused, double *out_6160852528093942108) {
  H_14(state, unused, out_6160852528093942108);
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
