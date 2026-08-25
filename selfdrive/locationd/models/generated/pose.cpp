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
void err_fun(double *nom_x, double *delta_x, double *out_4409321269442810496) {
   out_4409321269442810496[0] = delta_x[0] + nom_x[0];
   out_4409321269442810496[1] = delta_x[1] + nom_x[1];
   out_4409321269442810496[2] = delta_x[2] + nom_x[2];
   out_4409321269442810496[3] = delta_x[3] + nom_x[3];
   out_4409321269442810496[4] = delta_x[4] + nom_x[4];
   out_4409321269442810496[5] = delta_x[5] + nom_x[5];
   out_4409321269442810496[6] = delta_x[6] + nom_x[6];
   out_4409321269442810496[7] = delta_x[7] + nom_x[7];
   out_4409321269442810496[8] = delta_x[8] + nom_x[8];
   out_4409321269442810496[9] = delta_x[9] + nom_x[9];
   out_4409321269442810496[10] = delta_x[10] + nom_x[10];
   out_4409321269442810496[11] = delta_x[11] + nom_x[11];
   out_4409321269442810496[12] = delta_x[12] + nom_x[12];
   out_4409321269442810496[13] = delta_x[13] + nom_x[13];
   out_4409321269442810496[14] = delta_x[14] + nom_x[14];
   out_4409321269442810496[15] = delta_x[15] + nom_x[15];
   out_4409321269442810496[16] = delta_x[16] + nom_x[16];
   out_4409321269442810496[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3789556254182165506) {
   out_3789556254182165506[0] = -nom_x[0] + true_x[0];
   out_3789556254182165506[1] = -nom_x[1] + true_x[1];
   out_3789556254182165506[2] = -nom_x[2] + true_x[2];
   out_3789556254182165506[3] = -nom_x[3] + true_x[3];
   out_3789556254182165506[4] = -nom_x[4] + true_x[4];
   out_3789556254182165506[5] = -nom_x[5] + true_x[5];
   out_3789556254182165506[6] = -nom_x[6] + true_x[6];
   out_3789556254182165506[7] = -nom_x[7] + true_x[7];
   out_3789556254182165506[8] = -nom_x[8] + true_x[8];
   out_3789556254182165506[9] = -nom_x[9] + true_x[9];
   out_3789556254182165506[10] = -nom_x[10] + true_x[10];
   out_3789556254182165506[11] = -nom_x[11] + true_x[11];
   out_3789556254182165506[12] = -nom_x[12] + true_x[12];
   out_3789556254182165506[13] = -nom_x[13] + true_x[13];
   out_3789556254182165506[14] = -nom_x[14] + true_x[14];
   out_3789556254182165506[15] = -nom_x[15] + true_x[15];
   out_3789556254182165506[16] = -nom_x[16] + true_x[16];
   out_3789556254182165506[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3068405914716205428) {
   out_3068405914716205428[0] = 1.0;
   out_3068405914716205428[1] = 0.0;
   out_3068405914716205428[2] = 0.0;
   out_3068405914716205428[3] = 0.0;
   out_3068405914716205428[4] = 0.0;
   out_3068405914716205428[5] = 0.0;
   out_3068405914716205428[6] = 0.0;
   out_3068405914716205428[7] = 0.0;
   out_3068405914716205428[8] = 0.0;
   out_3068405914716205428[9] = 0.0;
   out_3068405914716205428[10] = 0.0;
   out_3068405914716205428[11] = 0.0;
   out_3068405914716205428[12] = 0.0;
   out_3068405914716205428[13] = 0.0;
   out_3068405914716205428[14] = 0.0;
   out_3068405914716205428[15] = 0.0;
   out_3068405914716205428[16] = 0.0;
   out_3068405914716205428[17] = 0.0;
   out_3068405914716205428[18] = 0.0;
   out_3068405914716205428[19] = 1.0;
   out_3068405914716205428[20] = 0.0;
   out_3068405914716205428[21] = 0.0;
   out_3068405914716205428[22] = 0.0;
   out_3068405914716205428[23] = 0.0;
   out_3068405914716205428[24] = 0.0;
   out_3068405914716205428[25] = 0.0;
   out_3068405914716205428[26] = 0.0;
   out_3068405914716205428[27] = 0.0;
   out_3068405914716205428[28] = 0.0;
   out_3068405914716205428[29] = 0.0;
   out_3068405914716205428[30] = 0.0;
   out_3068405914716205428[31] = 0.0;
   out_3068405914716205428[32] = 0.0;
   out_3068405914716205428[33] = 0.0;
   out_3068405914716205428[34] = 0.0;
   out_3068405914716205428[35] = 0.0;
   out_3068405914716205428[36] = 0.0;
   out_3068405914716205428[37] = 0.0;
   out_3068405914716205428[38] = 1.0;
   out_3068405914716205428[39] = 0.0;
   out_3068405914716205428[40] = 0.0;
   out_3068405914716205428[41] = 0.0;
   out_3068405914716205428[42] = 0.0;
   out_3068405914716205428[43] = 0.0;
   out_3068405914716205428[44] = 0.0;
   out_3068405914716205428[45] = 0.0;
   out_3068405914716205428[46] = 0.0;
   out_3068405914716205428[47] = 0.0;
   out_3068405914716205428[48] = 0.0;
   out_3068405914716205428[49] = 0.0;
   out_3068405914716205428[50] = 0.0;
   out_3068405914716205428[51] = 0.0;
   out_3068405914716205428[52] = 0.0;
   out_3068405914716205428[53] = 0.0;
   out_3068405914716205428[54] = 0.0;
   out_3068405914716205428[55] = 0.0;
   out_3068405914716205428[56] = 0.0;
   out_3068405914716205428[57] = 1.0;
   out_3068405914716205428[58] = 0.0;
   out_3068405914716205428[59] = 0.0;
   out_3068405914716205428[60] = 0.0;
   out_3068405914716205428[61] = 0.0;
   out_3068405914716205428[62] = 0.0;
   out_3068405914716205428[63] = 0.0;
   out_3068405914716205428[64] = 0.0;
   out_3068405914716205428[65] = 0.0;
   out_3068405914716205428[66] = 0.0;
   out_3068405914716205428[67] = 0.0;
   out_3068405914716205428[68] = 0.0;
   out_3068405914716205428[69] = 0.0;
   out_3068405914716205428[70] = 0.0;
   out_3068405914716205428[71] = 0.0;
   out_3068405914716205428[72] = 0.0;
   out_3068405914716205428[73] = 0.0;
   out_3068405914716205428[74] = 0.0;
   out_3068405914716205428[75] = 0.0;
   out_3068405914716205428[76] = 1.0;
   out_3068405914716205428[77] = 0.0;
   out_3068405914716205428[78] = 0.0;
   out_3068405914716205428[79] = 0.0;
   out_3068405914716205428[80] = 0.0;
   out_3068405914716205428[81] = 0.0;
   out_3068405914716205428[82] = 0.0;
   out_3068405914716205428[83] = 0.0;
   out_3068405914716205428[84] = 0.0;
   out_3068405914716205428[85] = 0.0;
   out_3068405914716205428[86] = 0.0;
   out_3068405914716205428[87] = 0.0;
   out_3068405914716205428[88] = 0.0;
   out_3068405914716205428[89] = 0.0;
   out_3068405914716205428[90] = 0.0;
   out_3068405914716205428[91] = 0.0;
   out_3068405914716205428[92] = 0.0;
   out_3068405914716205428[93] = 0.0;
   out_3068405914716205428[94] = 0.0;
   out_3068405914716205428[95] = 1.0;
   out_3068405914716205428[96] = 0.0;
   out_3068405914716205428[97] = 0.0;
   out_3068405914716205428[98] = 0.0;
   out_3068405914716205428[99] = 0.0;
   out_3068405914716205428[100] = 0.0;
   out_3068405914716205428[101] = 0.0;
   out_3068405914716205428[102] = 0.0;
   out_3068405914716205428[103] = 0.0;
   out_3068405914716205428[104] = 0.0;
   out_3068405914716205428[105] = 0.0;
   out_3068405914716205428[106] = 0.0;
   out_3068405914716205428[107] = 0.0;
   out_3068405914716205428[108] = 0.0;
   out_3068405914716205428[109] = 0.0;
   out_3068405914716205428[110] = 0.0;
   out_3068405914716205428[111] = 0.0;
   out_3068405914716205428[112] = 0.0;
   out_3068405914716205428[113] = 0.0;
   out_3068405914716205428[114] = 1.0;
   out_3068405914716205428[115] = 0.0;
   out_3068405914716205428[116] = 0.0;
   out_3068405914716205428[117] = 0.0;
   out_3068405914716205428[118] = 0.0;
   out_3068405914716205428[119] = 0.0;
   out_3068405914716205428[120] = 0.0;
   out_3068405914716205428[121] = 0.0;
   out_3068405914716205428[122] = 0.0;
   out_3068405914716205428[123] = 0.0;
   out_3068405914716205428[124] = 0.0;
   out_3068405914716205428[125] = 0.0;
   out_3068405914716205428[126] = 0.0;
   out_3068405914716205428[127] = 0.0;
   out_3068405914716205428[128] = 0.0;
   out_3068405914716205428[129] = 0.0;
   out_3068405914716205428[130] = 0.0;
   out_3068405914716205428[131] = 0.0;
   out_3068405914716205428[132] = 0.0;
   out_3068405914716205428[133] = 1.0;
   out_3068405914716205428[134] = 0.0;
   out_3068405914716205428[135] = 0.0;
   out_3068405914716205428[136] = 0.0;
   out_3068405914716205428[137] = 0.0;
   out_3068405914716205428[138] = 0.0;
   out_3068405914716205428[139] = 0.0;
   out_3068405914716205428[140] = 0.0;
   out_3068405914716205428[141] = 0.0;
   out_3068405914716205428[142] = 0.0;
   out_3068405914716205428[143] = 0.0;
   out_3068405914716205428[144] = 0.0;
   out_3068405914716205428[145] = 0.0;
   out_3068405914716205428[146] = 0.0;
   out_3068405914716205428[147] = 0.0;
   out_3068405914716205428[148] = 0.0;
   out_3068405914716205428[149] = 0.0;
   out_3068405914716205428[150] = 0.0;
   out_3068405914716205428[151] = 0.0;
   out_3068405914716205428[152] = 1.0;
   out_3068405914716205428[153] = 0.0;
   out_3068405914716205428[154] = 0.0;
   out_3068405914716205428[155] = 0.0;
   out_3068405914716205428[156] = 0.0;
   out_3068405914716205428[157] = 0.0;
   out_3068405914716205428[158] = 0.0;
   out_3068405914716205428[159] = 0.0;
   out_3068405914716205428[160] = 0.0;
   out_3068405914716205428[161] = 0.0;
   out_3068405914716205428[162] = 0.0;
   out_3068405914716205428[163] = 0.0;
   out_3068405914716205428[164] = 0.0;
   out_3068405914716205428[165] = 0.0;
   out_3068405914716205428[166] = 0.0;
   out_3068405914716205428[167] = 0.0;
   out_3068405914716205428[168] = 0.0;
   out_3068405914716205428[169] = 0.0;
   out_3068405914716205428[170] = 0.0;
   out_3068405914716205428[171] = 1.0;
   out_3068405914716205428[172] = 0.0;
   out_3068405914716205428[173] = 0.0;
   out_3068405914716205428[174] = 0.0;
   out_3068405914716205428[175] = 0.0;
   out_3068405914716205428[176] = 0.0;
   out_3068405914716205428[177] = 0.0;
   out_3068405914716205428[178] = 0.0;
   out_3068405914716205428[179] = 0.0;
   out_3068405914716205428[180] = 0.0;
   out_3068405914716205428[181] = 0.0;
   out_3068405914716205428[182] = 0.0;
   out_3068405914716205428[183] = 0.0;
   out_3068405914716205428[184] = 0.0;
   out_3068405914716205428[185] = 0.0;
   out_3068405914716205428[186] = 0.0;
   out_3068405914716205428[187] = 0.0;
   out_3068405914716205428[188] = 0.0;
   out_3068405914716205428[189] = 0.0;
   out_3068405914716205428[190] = 1.0;
   out_3068405914716205428[191] = 0.0;
   out_3068405914716205428[192] = 0.0;
   out_3068405914716205428[193] = 0.0;
   out_3068405914716205428[194] = 0.0;
   out_3068405914716205428[195] = 0.0;
   out_3068405914716205428[196] = 0.0;
   out_3068405914716205428[197] = 0.0;
   out_3068405914716205428[198] = 0.0;
   out_3068405914716205428[199] = 0.0;
   out_3068405914716205428[200] = 0.0;
   out_3068405914716205428[201] = 0.0;
   out_3068405914716205428[202] = 0.0;
   out_3068405914716205428[203] = 0.0;
   out_3068405914716205428[204] = 0.0;
   out_3068405914716205428[205] = 0.0;
   out_3068405914716205428[206] = 0.0;
   out_3068405914716205428[207] = 0.0;
   out_3068405914716205428[208] = 0.0;
   out_3068405914716205428[209] = 1.0;
   out_3068405914716205428[210] = 0.0;
   out_3068405914716205428[211] = 0.0;
   out_3068405914716205428[212] = 0.0;
   out_3068405914716205428[213] = 0.0;
   out_3068405914716205428[214] = 0.0;
   out_3068405914716205428[215] = 0.0;
   out_3068405914716205428[216] = 0.0;
   out_3068405914716205428[217] = 0.0;
   out_3068405914716205428[218] = 0.0;
   out_3068405914716205428[219] = 0.0;
   out_3068405914716205428[220] = 0.0;
   out_3068405914716205428[221] = 0.0;
   out_3068405914716205428[222] = 0.0;
   out_3068405914716205428[223] = 0.0;
   out_3068405914716205428[224] = 0.0;
   out_3068405914716205428[225] = 0.0;
   out_3068405914716205428[226] = 0.0;
   out_3068405914716205428[227] = 0.0;
   out_3068405914716205428[228] = 1.0;
   out_3068405914716205428[229] = 0.0;
   out_3068405914716205428[230] = 0.0;
   out_3068405914716205428[231] = 0.0;
   out_3068405914716205428[232] = 0.0;
   out_3068405914716205428[233] = 0.0;
   out_3068405914716205428[234] = 0.0;
   out_3068405914716205428[235] = 0.0;
   out_3068405914716205428[236] = 0.0;
   out_3068405914716205428[237] = 0.0;
   out_3068405914716205428[238] = 0.0;
   out_3068405914716205428[239] = 0.0;
   out_3068405914716205428[240] = 0.0;
   out_3068405914716205428[241] = 0.0;
   out_3068405914716205428[242] = 0.0;
   out_3068405914716205428[243] = 0.0;
   out_3068405914716205428[244] = 0.0;
   out_3068405914716205428[245] = 0.0;
   out_3068405914716205428[246] = 0.0;
   out_3068405914716205428[247] = 1.0;
   out_3068405914716205428[248] = 0.0;
   out_3068405914716205428[249] = 0.0;
   out_3068405914716205428[250] = 0.0;
   out_3068405914716205428[251] = 0.0;
   out_3068405914716205428[252] = 0.0;
   out_3068405914716205428[253] = 0.0;
   out_3068405914716205428[254] = 0.0;
   out_3068405914716205428[255] = 0.0;
   out_3068405914716205428[256] = 0.0;
   out_3068405914716205428[257] = 0.0;
   out_3068405914716205428[258] = 0.0;
   out_3068405914716205428[259] = 0.0;
   out_3068405914716205428[260] = 0.0;
   out_3068405914716205428[261] = 0.0;
   out_3068405914716205428[262] = 0.0;
   out_3068405914716205428[263] = 0.0;
   out_3068405914716205428[264] = 0.0;
   out_3068405914716205428[265] = 0.0;
   out_3068405914716205428[266] = 1.0;
   out_3068405914716205428[267] = 0.0;
   out_3068405914716205428[268] = 0.0;
   out_3068405914716205428[269] = 0.0;
   out_3068405914716205428[270] = 0.0;
   out_3068405914716205428[271] = 0.0;
   out_3068405914716205428[272] = 0.0;
   out_3068405914716205428[273] = 0.0;
   out_3068405914716205428[274] = 0.0;
   out_3068405914716205428[275] = 0.0;
   out_3068405914716205428[276] = 0.0;
   out_3068405914716205428[277] = 0.0;
   out_3068405914716205428[278] = 0.0;
   out_3068405914716205428[279] = 0.0;
   out_3068405914716205428[280] = 0.0;
   out_3068405914716205428[281] = 0.0;
   out_3068405914716205428[282] = 0.0;
   out_3068405914716205428[283] = 0.0;
   out_3068405914716205428[284] = 0.0;
   out_3068405914716205428[285] = 1.0;
   out_3068405914716205428[286] = 0.0;
   out_3068405914716205428[287] = 0.0;
   out_3068405914716205428[288] = 0.0;
   out_3068405914716205428[289] = 0.0;
   out_3068405914716205428[290] = 0.0;
   out_3068405914716205428[291] = 0.0;
   out_3068405914716205428[292] = 0.0;
   out_3068405914716205428[293] = 0.0;
   out_3068405914716205428[294] = 0.0;
   out_3068405914716205428[295] = 0.0;
   out_3068405914716205428[296] = 0.0;
   out_3068405914716205428[297] = 0.0;
   out_3068405914716205428[298] = 0.0;
   out_3068405914716205428[299] = 0.0;
   out_3068405914716205428[300] = 0.0;
   out_3068405914716205428[301] = 0.0;
   out_3068405914716205428[302] = 0.0;
   out_3068405914716205428[303] = 0.0;
   out_3068405914716205428[304] = 1.0;
   out_3068405914716205428[305] = 0.0;
   out_3068405914716205428[306] = 0.0;
   out_3068405914716205428[307] = 0.0;
   out_3068405914716205428[308] = 0.0;
   out_3068405914716205428[309] = 0.0;
   out_3068405914716205428[310] = 0.0;
   out_3068405914716205428[311] = 0.0;
   out_3068405914716205428[312] = 0.0;
   out_3068405914716205428[313] = 0.0;
   out_3068405914716205428[314] = 0.0;
   out_3068405914716205428[315] = 0.0;
   out_3068405914716205428[316] = 0.0;
   out_3068405914716205428[317] = 0.0;
   out_3068405914716205428[318] = 0.0;
   out_3068405914716205428[319] = 0.0;
   out_3068405914716205428[320] = 0.0;
   out_3068405914716205428[321] = 0.0;
   out_3068405914716205428[322] = 0.0;
   out_3068405914716205428[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_5515990809264108996) {
   out_5515990809264108996[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_5515990809264108996[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_5515990809264108996[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_5515990809264108996[3] = dt*state[12] + state[3];
   out_5515990809264108996[4] = dt*state[13] + state[4];
   out_5515990809264108996[5] = dt*state[14] + state[5];
   out_5515990809264108996[6] = state[6];
   out_5515990809264108996[7] = state[7];
   out_5515990809264108996[8] = state[8];
   out_5515990809264108996[9] = state[9];
   out_5515990809264108996[10] = state[10];
   out_5515990809264108996[11] = state[11];
   out_5515990809264108996[12] = state[12];
   out_5515990809264108996[13] = state[13];
   out_5515990809264108996[14] = state[14];
   out_5515990809264108996[15] = state[15];
   out_5515990809264108996[16] = state[16];
   out_5515990809264108996[17] = state[17];
}
void F_fun(double *state, double dt, double *out_1412435369220653896) {
   out_1412435369220653896[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1412435369220653896[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1412435369220653896[2] = 0;
   out_1412435369220653896[3] = 0;
   out_1412435369220653896[4] = 0;
   out_1412435369220653896[5] = 0;
   out_1412435369220653896[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1412435369220653896[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1412435369220653896[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_1412435369220653896[9] = 0;
   out_1412435369220653896[10] = 0;
   out_1412435369220653896[11] = 0;
   out_1412435369220653896[12] = 0;
   out_1412435369220653896[13] = 0;
   out_1412435369220653896[14] = 0;
   out_1412435369220653896[15] = 0;
   out_1412435369220653896[16] = 0;
   out_1412435369220653896[17] = 0;
   out_1412435369220653896[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1412435369220653896[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1412435369220653896[20] = 0;
   out_1412435369220653896[21] = 0;
   out_1412435369220653896[22] = 0;
   out_1412435369220653896[23] = 0;
   out_1412435369220653896[24] = 0;
   out_1412435369220653896[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1412435369220653896[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_1412435369220653896[27] = 0;
   out_1412435369220653896[28] = 0;
   out_1412435369220653896[29] = 0;
   out_1412435369220653896[30] = 0;
   out_1412435369220653896[31] = 0;
   out_1412435369220653896[32] = 0;
   out_1412435369220653896[33] = 0;
   out_1412435369220653896[34] = 0;
   out_1412435369220653896[35] = 0;
   out_1412435369220653896[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1412435369220653896[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1412435369220653896[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1412435369220653896[39] = 0;
   out_1412435369220653896[40] = 0;
   out_1412435369220653896[41] = 0;
   out_1412435369220653896[42] = 0;
   out_1412435369220653896[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1412435369220653896[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_1412435369220653896[45] = 0;
   out_1412435369220653896[46] = 0;
   out_1412435369220653896[47] = 0;
   out_1412435369220653896[48] = 0;
   out_1412435369220653896[49] = 0;
   out_1412435369220653896[50] = 0;
   out_1412435369220653896[51] = 0;
   out_1412435369220653896[52] = 0;
   out_1412435369220653896[53] = 0;
   out_1412435369220653896[54] = 0;
   out_1412435369220653896[55] = 0;
   out_1412435369220653896[56] = 0;
   out_1412435369220653896[57] = 1;
   out_1412435369220653896[58] = 0;
   out_1412435369220653896[59] = 0;
   out_1412435369220653896[60] = 0;
   out_1412435369220653896[61] = 0;
   out_1412435369220653896[62] = 0;
   out_1412435369220653896[63] = 0;
   out_1412435369220653896[64] = 0;
   out_1412435369220653896[65] = 0;
   out_1412435369220653896[66] = dt;
   out_1412435369220653896[67] = 0;
   out_1412435369220653896[68] = 0;
   out_1412435369220653896[69] = 0;
   out_1412435369220653896[70] = 0;
   out_1412435369220653896[71] = 0;
   out_1412435369220653896[72] = 0;
   out_1412435369220653896[73] = 0;
   out_1412435369220653896[74] = 0;
   out_1412435369220653896[75] = 0;
   out_1412435369220653896[76] = 1;
   out_1412435369220653896[77] = 0;
   out_1412435369220653896[78] = 0;
   out_1412435369220653896[79] = 0;
   out_1412435369220653896[80] = 0;
   out_1412435369220653896[81] = 0;
   out_1412435369220653896[82] = 0;
   out_1412435369220653896[83] = 0;
   out_1412435369220653896[84] = 0;
   out_1412435369220653896[85] = dt;
   out_1412435369220653896[86] = 0;
   out_1412435369220653896[87] = 0;
   out_1412435369220653896[88] = 0;
   out_1412435369220653896[89] = 0;
   out_1412435369220653896[90] = 0;
   out_1412435369220653896[91] = 0;
   out_1412435369220653896[92] = 0;
   out_1412435369220653896[93] = 0;
   out_1412435369220653896[94] = 0;
   out_1412435369220653896[95] = 1;
   out_1412435369220653896[96] = 0;
   out_1412435369220653896[97] = 0;
   out_1412435369220653896[98] = 0;
   out_1412435369220653896[99] = 0;
   out_1412435369220653896[100] = 0;
   out_1412435369220653896[101] = 0;
   out_1412435369220653896[102] = 0;
   out_1412435369220653896[103] = 0;
   out_1412435369220653896[104] = dt;
   out_1412435369220653896[105] = 0;
   out_1412435369220653896[106] = 0;
   out_1412435369220653896[107] = 0;
   out_1412435369220653896[108] = 0;
   out_1412435369220653896[109] = 0;
   out_1412435369220653896[110] = 0;
   out_1412435369220653896[111] = 0;
   out_1412435369220653896[112] = 0;
   out_1412435369220653896[113] = 0;
   out_1412435369220653896[114] = 1;
   out_1412435369220653896[115] = 0;
   out_1412435369220653896[116] = 0;
   out_1412435369220653896[117] = 0;
   out_1412435369220653896[118] = 0;
   out_1412435369220653896[119] = 0;
   out_1412435369220653896[120] = 0;
   out_1412435369220653896[121] = 0;
   out_1412435369220653896[122] = 0;
   out_1412435369220653896[123] = 0;
   out_1412435369220653896[124] = 0;
   out_1412435369220653896[125] = 0;
   out_1412435369220653896[126] = 0;
   out_1412435369220653896[127] = 0;
   out_1412435369220653896[128] = 0;
   out_1412435369220653896[129] = 0;
   out_1412435369220653896[130] = 0;
   out_1412435369220653896[131] = 0;
   out_1412435369220653896[132] = 0;
   out_1412435369220653896[133] = 1;
   out_1412435369220653896[134] = 0;
   out_1412435369220653896[135] = 0;
   out_1412435369220653896[136] = 0;
   out_1412435369220653896[137] = 0;
   out_1412435369220653896[138] = 0;
   out_1412435369220653896[139] = 0;
   out_1412435369220653896[140] = 0;
   out_1412435369220653896[141] = 0;
   out_1412435369220653896[142] = 0;
   out_1412435369220653896[143] = 0;
   out_1412435369220653896[144] = 0;
   out_1412435369220653896[145] = 0;
   out_1412435369220653896[146] = 0;
   out_1412435369220653896[147] = 0;
   out_1412435369220653896[148] = 0;
   out_1412435369220653896[149] = 0;
   out_1412435369220653896[150] = 0;
   out_1412435369220653896[151] = 0;
   out_1412435369220653896[152] = 1;
   out_1412435369220653896[153] = 0;
   out_1412435369220653896[154] = 0;
   out_1412435369220653896[155] = 0;
   out_1412435369220653896[156] = 0;
   out_1412435369220653896[157] = 0;
   out_1412435369220653896[158] = 0;
   out_1412435369220653896[159] = 0;
   out_1412435369220653896[160] = 0;
   out_1412435369220653896[161] = 0;
   out_1412435369220653896[162] = 0;
   out_1412435369220653896[163] = 0;
   out_1412435369220653896[164] = 0;
   out_1412435369220653896[165] = 0;
   out_1412435369220653896[166] = 0;
   out_1412435369220653896[167] = 0;
   out_1412435369220653896[168] = 0;
   out_1412435369220653896[169] = 0;
   out_1412435369220653896[170] = 0;
   out_1412435369220653896[171] = 1;
   out_1412435369220653896[172] = 0;
   out_1412435369220653896[173] = 0;
   out_1412435369220653896[174] = 0;
   out_1412435369220653896[175] = 0;
   out_1412435369220653896[176] = 0;
   out_1412435369220653896[177] = 0;
   out_1412435369220653896[178] = 0;
   out_1412435369220653896[179] = 0;
   out_1412435369220653896[180] = 0;
   out_1412435369220653896[181] = 0;
   out_1412435369220653896[182] = 0;
   out_1412435369220653896[183] = 0;
   out_1412435369220653896[184] = 0;
   out_1412435369220653896[185] = 0;
   out_1412435369220653896[186] = 0;
   out_1412435369220653896[187] = 0;
   out_1412435369220653896[188] = 0;
   out_1412435369220653896[189] = 0;
   out_1412435369220653896[190] = 1;
   out_1412435369220653896[191] = 0;
   out_1412435369220653896[192] = 0;
   out_1412435369220653896[193] = 0;
   out_1412435369220653896[194] = 0;
   out_1412435369220653896[195] = 0;
   out_1412435369220653896[196] = 0;
   out_1412435369220653896[197] = 0;
   out_1412435369220653896[198] = 0;
   out_1412435369220653896[199] = 0;
   out_1412435369220653896[200] = 0;
   out_1412435369220653896[201] = 0;
   out_1412435369220653896[202] = 0;
   out_1412435369220653896[203] = 0;
   out_1412435369220653896[204] = 0;
   out_1412435369220653896[205] = 0;
   out_1412435369220653896[206] = 0;
   out_1412435369220653896[207] = 0;
   out_1412435369220653896[208] = 0;
   out_1412435369220653896[209] = 1;
   out_1412435369220653896[210] = 0;
   out_1412435369220653896[211] = 0;
   out_1412435369220653896[212] = 0;
   out_1412435369220653896[213] = 0;
   out_1412435369220653896[214] = 0;
   out_1412435369220653896[215] = 0;
   out_1412435369220653896[216] = 0;
   out_1412435369220653896[217] = 0;
   out_1412435369220653896[218] = 0;
   out_1412435369220653896[219] = 0;
   out_1412435369220653896[220] = 0;
   out_1412435369220653896[221] = 0;
   out_1412435369220653896[222] = 0;
   out_1412435369220653896[223] = 0;
   out_1412435369220653896[224] = 0;
   out_1412435369220653896[225] = 0;
   out_1412435369220653896[226] = 0;
   out_1412435369220653896[227] = 0;
   out_1412435369220653896[228] = 1;
   out_1412435369220653896[229] = 0;
   out_1412435369220653896[230] = 0;
   out_1412435369220653896[231] = 0;
   out_1412435369220653896[232] = 0;
   out_1412435369220653896[233] = 0;
   out_1412435369220653896[234] = 0;
   out_1412435369220653896[235] = 0;
   out_1412435369220653896[236] = 0;
   out_1412435369220653896[237] = 0;
   out_1412435369220653896[238] = 0;
   out_1412435369220653896[239] = 0;
   out_1412435369220653896[240] = 0;
   out_1412435369220653896[241] = 0;
   out_1412435369220653896[242] = 0;
   out_1412435369220653896[243] = 0;
   out_1412435369220653896[244] = 0;
   out_1412435369220653896[245] = 0;
   out_1412435369220653896[246] = 0;
   out_1412435369220653896[247] = 1;
   out_1412435369220653896[248] = 0;
   out_1412435369220653896[249] = 0;
   out_1412435369220653896[250] = 0;
   out_1412435369220653896[251] = 0;
   out_1412435369220653896[252] = 0;
   out_1412435369220653896[253] = 0;
   out_1412435369220653896[254] = 0;
   out_1412435369220653896[255] = 0;
   out_1412435369220653896[256] = 0;
   out_1412435369220653896[257] = 0;
   out_1412435369220653896[258] = 0;
   out_1412435369220653896[259] = 0;
   out_1412435369220653896[260] = 0;
   out_1412435369220653896[261] = 0;
   out_1412435369220653896[262] = 0;
   out_1412435369220653896[263] = 0;
   out_1412435369220653896[264] = 0;
   out_1412435369220653896[265] = 0;
   out_1412435369220653896[266] = 1;
   out_1412435369220653896[267] = 0;
   out_1412435369220653896[268] = 0;
   out_1412435369220653896[269] = 0;
   out_1412435369220653896[270] = 0;
   out_1412435369220653896[271] = 0;
   out_1412435369220653896[272] = 0;
   out_1412435369220653896[273] = 0;
   out_1412435369220653896[274] = 0;
   out_1412435369220653896[275] = 0;
   out_1412435369220653896[276] = 0;
   out_1412435369220653896[277] = 0;
   out_1412435369220653896[278] = 0;
   out_1412435369220653896[279] = 0;
   out_1412435369220653896[280] = 0;
   out_1412435369220653896[281] = 0;
   out_1412435369220653896[282] = 0;
   out_1412435369220653896[283] = 0;
   out_1412435369220653896[284] = 0;
   out_1412435369220653896[285] = 1;
   out_1412435369220653896[286] = 0;
   out_1412435369220653896[287] = 0;
   out_1412435369220653896[288] = 0;
   out_1412435369220653896[289] = 0;
   out_1412435369220653896[290] = 0;
   out_1412435369220653896[291] = 0;
   out_1412435369220653896[292] = 0;
   out_1412435369220653896[293] = 0;
   out_1412435369220653896[294] = 0;
   out_1412435369220653896[295] = 0;
   out_1412435369220653896[296] = 0;
   out_1412435369220653896[297] = 0;
   out_1412435369220653896[298] = 0;
   out_1412435369220653896[299] = 0;
   out_1412435369220653896[300] = 0;
   out_1412435369220653896[301] = 0;
   out_1412435369220653896[302] = 0;
   out_1412435369220653896[303] = 0;
   out_1412435369220653896[304] = 1;
   out_1412435369220653896[305] = 0;
   out_1412435369220653896[306] = 0;
   out_1412435369220653896[307] = 0;
   out_1412435369220653896[308] = 0;
   out_1412435369220653896[309] = 0;
   out_1412435369220653896[310] = 0;
   out_1412435369220653896[311] = 0;
   out_1412435369220653896[312] = 0;
   out_1412435369220653896[313] = 0;
   out_1412435369220653896[314] = 0;
   out_1412435369220653896[315] = 0;
   out_1412435369220653896[316] = 0;
   out_1412435369220653896[317] = 0;
   out_1412435369220653896[318] = 0;
   out_1412435369220653896[319] = 0;
   out_1412435369220653896[320] = 0;
   out_1412435369220653896[321] = 0;
   out_1412435369220653896[322] = 0;
   out_1412435369220653896[323] = 1;
}
void h_4(double *state, double *unused, double *out_7211674724064901455) {
   out_7211674724064901455[0] = state[6] + state[9];
   out_7211674724064901455[1] = state[7] + state[10];
   out_7211674724064901455[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_8220924299755286163) {
   out_8220924299755286163[0] = 0;
   out_8220924299755286163[1] = 0;
   out_8220924299755286163[2] = 0;
   out_8220924299755286163[3] = 0;
   out_8220924299755286163[4] = 0;
   out_8220924299755286163[5] = 0;
   out_8220924299755286163[6] = 1;
   out_8220924299755286163[7] = 0;
   out_8220924299755286163[8] = 0;
   out_8220924299755286163[9] = 1;
   out_8220924299755286163[10] = 0;
   out_8220924299755286163[11] = 0;
   out_8220924299755286163[12] = 0;
   out_8220924299755286163[13] = 0;
   out_8220924299755286163[14] = 0;
   out_8220924299755286163[15] = 0;
   out_8220924299755286163[16] = 0;
   out_8220924299755286163[17] = 0;
   out_8220924299755286163[18] = 0;
   out_8220924299755286163[19] = 0;
   out_8220924299755286163[20] = 0;
   out_8220924299755286163[21] = 0;
   out_8220924299755286163[22] = 0;
   out_8220924299755286163[23] = 0;
   out_8220924299755286163[24] = 0;
   out_8220924299755286163[25] = 1;
   out_8220924299755286163[26] = 0;
   out_8220924299755286163[27] = 0;
   out_8220924299755286163[28] = 1;
   out_8220924299755286163[29] = 0;
   out_8220924299755286163[30] = 0;
   out_8220924299755286163[31] = 0;
   out_8220924299755286163[32] = 0;
   out_8220924299755286163[33] = 0;
   out_8220924299755286163[34] = 0;
   out_8220924299755286163[35] = 0;
   out_8220924299755286163[36] = 0;
   out_8220924299755286163[37] = 0;
   out_8220924299755286163[38] = 0;
   out_8220924299755286163[39] = 0;
   out_8220924299755286163[40] = 0;
   out_8220924299755286163[41] = 0;
   out_8220924299755286163[42] = 0;
   out_8220924299755286163[43] = 0;
   out_8220924299755286163[44] = 1;
   out_8220924299755286163[45] = 0;
   out_8220924299755286163[46] = 0;
   out_8220924299755286163[47] = 1;
   out_8220924299755286163[48] = 0;
   out_8220924299755286163[49] = 0;
   out_8220924299755286163[50] = 0;
   out_8220924299755286163[51] = 0;
   out_8220924299755286163[52] = 0;
   out_8220924299755286163[53] = 0;
}
void h_10(double *state, double *unused, double *out_7091555343827122853) {
   out_7091555343827122853[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_7091555343827122853[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_7091555343827122853[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_3357399461201359920) {
   out_3357399461201359920[0] = 0;
   out_3357399461201359920[1] = 9.8100000000000005*cos(state[1]);
   out_3357399461201359920[2] = 0;
   out_3357399461201359920[3] = 0;
   out_3357399461201359920[4] = -state[8];
   out_3357399461201359920[5] = state[7];
   out_3357399461201359920[6] = 0;
   out_3357399461201359920[7] = state[5];
   out_3357399461201359920[8] = -state[4];
   out_3357399461201359920[9] = 0;
   out_3357399461201359920[10] = 0;
   out_3357399461201359920[11] = 0;
   out_3357399461201359920[12] = 1;
   out_3357399461201359920[13] = 0;
   out_3357399461201359920[14] = 0;
   out_3357399461201359920[15] = 1;
   out_3357399461201359920[16] = 0;
   out_3357399461201359920[17] = 0;
   out_3357399461201359920[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_3357399461201359920[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_3357399461201359920[20] = 0;
   out_3357399461201359920[21] = state[8];
   out_3357399461201359920[22] = 0;
   out_3357399461201359920[23] = -state[6];
   out_3357399461201359920[24] = -state[5];
   out_3357399461201359920[25] = 0;
   out_3357399461201359920[26] = state[3];
   out_3357399461201359920[27] = 0;
   out_3357399461201359920[28] = 0;
   out_3357399461201359920[29] = 0;
   out_3357399461201359920[30] = 0;
   out_3357399461201359920[31] = 1;
   out_3357399461201359920[32] = 0;
   out_3357399461201359920[33] = 0;
   out_3357399461201359920[34] = 1;
   out_3357399461201359920[35] = 0;
   out_3357399461201359920[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_3357399461201359920[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_3357399461201359920[38] = 0;
   out_3357399461201359920[39] = -state[7];
   out_3357399461201359920[40] = state[6];
   out_3357399461201359920[41] = 0;
   out_3357399461201359920[42] = state[4];
   out_3357399461201359920[43] = -state[3];
   out_3357399461201359920[44] = 0;
   out_3357399461201359920[45] = 0;
   out_3357399461201359920[46] = 0;
   out_3357399461201359920[47] = 0;
   out_3357399461201359920[48] = 0;
   out_3357399461201359920[49] = 0;
   out_3357399461201359920[50] = 1;
   out_3357399461201359920[51] = 0;
   out_3357399461201359920[52] = 0;
   out_3357399461201359920[53] = 1;
}
void h_13(double *state, double *unused, double *out_4463366606757688719) {
   out_4463366606757688719[0] = state[3];
   out_4463366606757688719[1] = state[4];
   out_4463366606757688719[2] = state[5];
}
void H_13(double *state, double *unused, double *out_7013545948621932652) {
   out_7013545948621932652[0] = 0;
   out_7013545948621932652[1] = 0;
   out_7013545948621932652[2] = 0;
   out_7013545948621932652[3] = 1;
   out_7013545948621932652[4] = 0;
   out_7013545948621932652[5] = 0;
   out_7013545948621932652[6] = 0;
   out_7013545948621932652[7] = 0;
   out_7013545948621932652[8] = 0;
   out_7013545948621932652[9] = 0;
   out_7013545948621932652[10] = 0;
   out_7013545948621932652[11] = 0;
   out_7013545948621932652[12] = 0;
   out_7013545948621932652[13] = 0;
   out_7013545948621932652[14] = 0;
   out_7013545948621932652[15] = 0;
   out_7013545948621932652[16] = 0;
   out_7013545948621932652[17] = 0;
   out_7013545948621932652[18] = 0;
   out_7013545948621932652[19] = 0;
   out_7013545948621932652[20] = 0;
   out_7013545948621932652[21] = 0;
   out_7013545948621932652[22] = 1;
   out_7013545948621932652[23] = 0;
   out_7013545948621932652[24] = 0;
   out_7013545948621932652[25] = 0;
   out_7013545948621932652[26] = 0;
   out_7013545948621932652[27] = 0;
   out_7013545948621932652[28] = 0;
   out_7013545948621932652[29] = 0;
   out_7013545948621932652[30] = 0;
   out_7013545948621932652[31] = 0;
   out_7013545948621932652[32] = 0;
   out_7013545948621932652[33] = 0;
   out_7013545948621932652[34] = 0;
   out_7013545948621932652[35] = 0;
   out_7013545948621932652[36] = 0;
   out_7013545948621932652[37] = 0;
   out_7013545948621932652[38] = 0;
   out_7013545948621932652[39] = 0;
   out_7013545948621932652[40] = 0;
   out_7013545948621932652[41] = 1;
   out_7013545948621932652[42] = 0;
   out_7013545948621932652[43] = 0;
   out_7013545948621932652[44] = 0;
   out_7013545948621932652[45] = 0;
   out_7013545948621932652[46] = 0;
   out_7013545948621932652[47] = 0;
   out_7013545948621932652[48] = 0;
   out_7013545948621932652[49] = 0;
   out_7013545948621932652[50] = 0;
   out_7013545948621932652[51] = 0;
   out_7013545948621932652[52] = 0;
   out_7013545948621932652[53] = 0;
}
void h_14(double *state, double *unused, double *out_2594435200759890716) {
   out_2594435200759890716[0] = state[6];
   out_2594435200759890716[1] = state[7];
   out_2594435200759890716[2] = state[8];
}
void H_14(double *state, double *unused, double *out_6262578917614780924) {
   out_6262578917614780924[0] = 0;
   out_6262578917614780924[1] = 0;
   out_6262578917614780924[2] = 0;
   out_6262578917614780924[3] = 0;
   out_6262578917614780924[4] = 0;
   out_6262578917614780924[5] = 0;
   out_6262578917614780924[6] = 1;
   out_6262578917614780924[7] = 0;
   out_6262578917614780924[8] = 0;
   out_6262578917614780924[9] = 0;
   out_6262578917614780924[10] = 0;
   out_6262578917614780924[11] = 0;
   out_6262578917614780924[12] = 0;
   out_6262578917614780924[13] = 0;
   out_6262578917614780924[14] = 0;
   out_6262578917614780924[15] = 0;
   out_6262578917614780924[16] = 0;
   out_6262578917614780924[17] = 0;
   out_6262578917614780924[18] = 0;
   out_6262578917614780924[19] = 0;
   out_6262578917614780924[20] = 0;
   out_6262578917614780924[21] = 0;
   out_6262578917614780924[22] = 0;
   out_6262578917614780924[23] = 0;
   out_6262578917614780924[24] = 0;
   out_6262578917614780924[25] = 1;
   out_6262578917614780924[26] = 0;
   out_6262578917614780924[27] = 0;
   out_6262578917614780924[28] = 0;
   out_6262578917614780924[29] = 0;
   out_6262578917614780924[30] = 0;
   out_6262578917614780924[31] = 0;
   out_6262578917614780924[32] = 0;
   out_6262578917614780924[33] = 0;
   out_6262578917614780924[34] = 0;
   out_6262578917614780924[35] = 0;
   out_6262578917614780924[36] = 0;
   out_6262578917614780924[37] = 0;
   out_6262578917614780924[38] = 0;
   out_6262578917614780924[39] = 0;
   out_6262578917614780924[40] = 0;
   out_6262578917614780924[41] = 0;
   out_6262578917614780924[42] = 0;
   out_6262578917614780924[43] = 0;
   out_6262578917614780924[44] = 1;
   out_6262578917614780924[45] = 0;
   out_6262578917614780924[46] = 0;
   out_6262578917614780924[47] = 0;
   out_6262578917614780924[48] = 0;
   out_6262578917614780924[49] = 0;
   out_6262578917614780924[50] = 0;
   out_6262578917614780924[51] = 0;
   out_6262578917614780924[52] = 0;
   out_6262578917614780924[53] = 0;
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
void pose_err_fun(double *nom_x, double *delta_x, double *out_4409321269442810496) {
  err_fun(nom_x, delta_x, out_4409321269442810496);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_3789556254182165506) {
  inv_err_fun(nom_x, true_x, out_3789556254182165506);
}
void pose_H_mod_fun(double *state, double *out_3068405914716205428) {
  H_mod_fun(state, out_3068405914716205428);
}
void pose_f_fun(double *state, double dt, double *out_5515990809264108996) {
  f_fun(state,  dt, out_5515990809264108996);
}
void pose_F_fun(double *state, double dt, double *out_1412435369220653896) {
  F_fun(state,  dt, out_1412435369220653896);
}
void pose_h_4(double *state, double *unused, double *out_7211674724064901455) {
  h_4(state, unused, out_7211674724064901455);
}
void pose_H_4(double *state, double *unused, double *out_8220924299755286163) {
  H_4(state, unused, out_8220924299755286163);
}
void pose_h_10(double *state, double *unused, double *out_7091555343827122853) {
  h_10(state, unused, out_7091555343827122853);
}
void pose_H_10(double *state, double *unused, double *out_3357399461201359920) {
  H_10(state, unused, out_3357399461201359920);
}
void pose_h_13(double *state, double *unused, double *out_4463366606757688719) {
  h_13(state, unused, out_4463366606757688719);
}
void pose_H_13(double *state, double *unused, double *out_7013545948621932652) {
  H_13(state, unused, out_7013545948621932652);
}
void pose_h_14(double *state, double *unused, double *out_2594435200759890716) {
  h_14(state, unused, out_2594435200759890716);
}
void pose_H_14(double *state, double *unused, double *out_6262578917614780924) {
  H_14(state, unused, out_6262578917614780924);
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
